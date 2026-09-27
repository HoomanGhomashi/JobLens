namespace JobLens.API.DTOs;

public class SearchHistoryDto
{
    public int Id { get; init; }
    public string? Geography { get; init; }
    public string? City { get; init; }
    public string? Department { get; init; }
    public string? SearchType { get; init; }
    public IReadOnlyList<string> QueriesUsed { get; init; } = [];
    public IReadOnlyList<string> SourcesChecked { get; init; } = [];
    public string? ApifyRunId { get; init; }
    public int CompaniesFound { get; init; }
    public int NewCompanies { get; init; }
    public int DuplicatesFound { get; init; }
    public int JobsFound { get; init; }
    public int NewJobs { get; init; }
    public string? CoverageState { get; init; }
    public string? Notes { get; init; }
    public DateTime SearchedAt { get; init; }
}
