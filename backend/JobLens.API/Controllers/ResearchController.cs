using System.Text.Json;
using JobLens.API.Data;
using JobLens.API.DTOs;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace JobLens.API.Controllers;

/// <summary>
/// Read-only endpoints over the research-engine's SQL Server data (research.* schema).
/// This controller never writes to those tables — research-engine is the sole writer.
/// </summary>
[ApiController]
[Route("api/research")]
public class ResearchController(ResearchDbContext db, ILogger<ResearchController> logger) : ControllerBase
{
    private const int DefaultPageSize = 20;
    private const int MaxPageSize = 100;

    [HttpGet("overview")]
    public async Task<ActionResult<OverviewDto>> GetOverview(CancellationToken cancellationToken)
    {
        try
        {
            var companiesCount = await db.Companies.CountAsync(cancellationToken);
            var jobsCount = await db.Jobs.CountAsync(cancellationToken);
            var activeOpportunitiesCount = await db.Jobs.CountAsync(j => j.IsActiveOpportunity, cancellationToken);
            var jobSourcesCount = await db.JobSources.CountAsync(cancellationToken);
            var searchHistoryCount = await db.SearchHistory.CountAsync(cancellationToken);

            var lastSearch = await db.SearchHistory
                .OrderByDescending(s => s.SearchedAt)
                .Select(s => new { s.SearchedAt, s.CoverageState })
                .FirstOrDefaultAsync(cancellationToken);

            var recentJobs = await ProjectJobDto(db.Jobs.AsNoTracking())
                .OrderByDescending(j => j.FirstDiscoveredAt)
                .Take(5)
                .ToListAsync(cancellationToken);

            return Ok(new OverviewDto
            {
                CompaniesCount = companiesCount,
                JobsCount = jobsCount,
                ActiveOpportunitiesCount = activeOpportunitiesCount,
                JobSourcesCount = jobSourcesCount,
                SearchHistoryCount = searchHistoryCount,
                LastSearchAt = lastSearch?.SearchedAt,
                LastCoverageState = lastSearch?.CoverageState,
                RecentJobs = recentJobs,
            });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to build research overview");
            return Problem("Unable to load overview data.", statusCode: StatusCodes.Status500InternalServerError);
        }
    }

    [HttpGet("companies")]
    public async Task<ActionResult<PagedResult<CompanyDto>>> GetCompanies(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = DefaultPageSize,
        CancellationToken cancellationToken = default)
    {
        (page, pageSize) = NormalizePaging(page, pageSize);

        try
        {
            var query = db.Companies.AsNoTracking().OrderByDescending(c => c.LastResearchedAt ?? c.FirstDiscoveredAt);

            var totalCount = await query.CountAsync(cancellationToken);
            var items = await query
                .Skip((page - 1) * pageSize)
                .Take(pageSize)
                .Select(c => new CompanyDto
                {
                    Id = c.Id,
                    Name = c.Name,
                    Domain = c.Domain,
                    Website = c.Website,
                    City = c.City,
                    Department = c.Department,
                    CompanyType = c.CompanyType,
                    Sector = c.Sector,
                    JuniorHiringSignal = c.JuniorHiringSignal,
                    HiringHistorySignal = c.HiringHistorySignal,
                    FrenchLanguageSignal = c.FrenchLanguageSignal,
                    Status = c.Status,
                    RelevanceReason = c.RelevanceReason,
                    FirstDiscoveredAt = c.FirstDiscoveredAt,
                    LastResearchedAt = c.LastResearchedAt,
                    LastRelevantVacancyAt = c.LastRelevantVacancyAt,
                })
                .ToListAsync(cancellationToken);

            return Ok(new PagedResult<CompanyDto> { Items = items, TotalCount = totalCount, Page = page, PageSize = pageSize });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load companies");
            return Problem("Unable to load companies.", statusCode: StatusCodes.Status500InternalServerError);
        }
    }

    [HttpGet("jobs")]
    public async Task<ActionResult<PagedResult<JobDto>>> GetJobs(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = DefaultPageSize,
        CancellationToken cancellationToken = default)
    {
        (page, pageSize) = NormalizePaging(page, pageSize);

        try
        {
            var query = db.Jobs.AsNoTracking().OrderByDescending(j => j.FirstDiscoveredAt);

            var totalCount = await query.CountAsync(cancellationToken);
            var items = await ProjectJobDto(query)
                .Skip((page - 1) * pageSize)
                .Take(pageSize)
                .ToListAsync(cancellationToken);

            return Ok(new PagedResult<JobDto> { Items = items, TotalCount = totalCount, Page = page, PageSize = pageSize });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load jobs");
            return Problem("Unable to load jobs.", statusCode: StatusCodes.Status500InternalServerError);
        }
    }

    [HttpGet("job-sources")]
    public async Task<ActionResult<PagedResult<JobSourceDto>>> GetJobSources(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = DefaultPageSize,
        CancellationToken cancellationToken = default)
    {
        (page, pageSize) = NormalizePaging(page, pageSize);

        try
        {
            var query = db.JobSources.AsNoTracking().OrderByDescending(s => s.DiscoveredAt);

            var totalCount = await query.CountAsync(cancellationToken);
            var items = await query
                .Skip((page - 1) * pageSize)
                .Take(pageSize)
                .Select(s => new JobSourceDto
                {
                    Id = s.Id,
                    JobId = s.JobId,
                    JobTitle = s.Job != null ? s.Job.Title : null,
                    Source = s.Source,
                    SourceUrl = s.SourceUrl,
                    UrlVerified = s.UrlVerified,
                    UrlReliable = s.UrlReliable,
                    PageTitle = s.PageTitle,
                    DiscoveredAt = s.DiscoveredAt,
                    VerifiedAt = s.VerifiedAt,
                })
                .ToListAsync(cancellationToken);

            return Ok(new PagedResult<JobSourceDto> { Items = items, TotalCount = totalCount, Page = page, PageSize = pageSize });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load job sources");
            return Problem("Unable to load job sources.", statusCode: StatusCodes.Status500InternalServerError);
        }
    }

    [HttpGet("search-history")]
    public async Task<ActionResult<PagedResult<SearchHistoryDto>>> GetSearchHistory(
        [FromQuery] int page = 1,
        [FromQuery] int pageSize = DefaultPageSize,
        CancellationToken cancellationToken = default)
    {
        (page, pageSize) = NormalizePaging(page, pageSize);

        try
        {
            var query = db.SearchHistory.AsNoTracking().OrderByDescending(s => s.SearchedAt);

            var totalCount = await query.CountAsync(cancellationToken);
            var rows = await query
                .Skip((page - 1) * pageSize)
                .Take(pageSize)
                .ToListAsync(cancellationToken);

            var items = rows.Select(s => new SearchHistoryDto
            {
                Id = s.Id,
                Geography = s.Geography,
                City = s.City,
                Department = s.Department,
                SearchType = s.SearchType,
                QueriesUsed = ParseJsonStringArray(s.QueriesUsed),
                SourcesChecked = ParseJsonStringArray(s.SourcesChecked),
                ApifyRunId = s.ApifyRunId,
                CompaniesFound = s.CompaniesFound,
                NewCompanies = s.NewCompanies,
                DuplicatesFound = s.DuplicatesFound,
                JobsFound = s.JobsFound,
                NewJobs = s.NewJobs,
                CoverageState = s.CoverageState,
                Notes = s.Notes,
                SearchedAt = s.SearchedAt,
            }).ToList();

            return Ok(new PagedResult<SearchHistoryDto> { Items = items, TotalCount = totalCount, Page = page, PageSize = pageSize });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load search history");
            return Problem("Unable to load search history.", statusCode: StatusCodes.Status500InternalServerError);
        }
    }

    private static IQueryable<JobDto> ProjectJobDto(IQueryable<Models.Job> source) =>
        source.Select(j => new JobDto
        {
            Id = j.Id,
            Title = j.Title,
            CompanyName = j.Company != null ? j.Company.Name : null,
            City = j.City,
            Country = j.Country,
            PublishedAt = j.PublishedAt,
            PublishedAtRaw = j.PublishedAtRaw,
            ContractType = j.ContractType,
            Description = j.Description,
            ExperienceMinYears = j.ExperienceMinYears,
            ExperienceMaxYears = j.ExperienceMaxYears,
            ExperienceRaw = j.ExperienceRaw,
            IsActiveOpportunity = j.IsActiveOpportunity,
            Status = j.Status,
            FirstDiscoveredAt = j.FirstDiscoveredAt,
            LastSeenAt = j.LastSeenAt,
            Sources = j.Sources.Select(s => new JobSourceDto
            {
                Id = s.Id,
                JobId = s.JobId,
                JobTitle = j.Title,
                Source = s.Source,
                SourceUrl = s.SourceUrl,
                UrlVerified = s.UrlVerified,
                UrlReliable = s.UrlReliable,
                PageTitle = s.PageTitle,
                DiscoveredAt = s.DiscoveredAt,
                VerifiedAt = s.VerifiedAt,
            }).ToList(),
        });

    private static (int page, int pageSize) NormalizePaging(int page, int pageSize)
    {
        page = page < 1 ? 1 : page;
        pageSize = pageSize < 1 ? DefaultPageSize : Math.Min(pageSize, MaxPageSize);
        return (page, pageSize);
    }

    private static List<string> ParseJsonStringArray(string? json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return [];
        }

        try
        {
            return JsonSerializer.Deserialize<List<string>>(json) ?? [];
        }
        catch (JsonException)
        {
            return [];
        }
    }
}
