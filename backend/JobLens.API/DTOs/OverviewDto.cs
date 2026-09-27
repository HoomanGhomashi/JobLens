namespace JobLens.API.DTOs;

public class OverviewDto
{
    public int CompaniesCount { get; init; }
    public int JobsCount { get; init; }
    public int ActiveOpportunitiesCount { get; init; }
    public int JobSourcesCount { get; init; }
    public int SearchHistoryCount { get; init; }
    public DateTime? LastSearchAt { get; init; }
    public string? LastCoverageState { get; init; }
    public IReadOnlyList<JobDto> RecentJobs { get; init; } = [];
}
