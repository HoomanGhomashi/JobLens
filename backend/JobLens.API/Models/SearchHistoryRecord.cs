namespace JobLens.API.Models;

/// <summary>
/// Maps to research.SearchHistory (owned by the Python research-engine — read-only from this API).
/// NOTE: there is no single "query"/"source"/"status" column — QueriesUsed and SourcesChecked are
/// JSON arrays (stored as NVARCHAR(MAX)), and CoverageState (COMPLETE/PARTIAL/FAILED) is the closest
/// equivalent to a "status".
/// </summary>
public class SearchHistoryRecord
{
    public int Id { get; set; }

    public string? Geography { get; set; }
    public string? City { get; set; }
    public string? Department { get; set; }

    public string? SearchType { get; set; }
    public string? QueriesUsed { get; set; }
    public string? SourcesChecked { get; set; }

    public string? ApifyRunId { get; set; }

    public int CompaniesFound { get; set; }
    public int NewCompanies { get; set; }
    public int DuplicatesFound { get; set; }
    public int JobsFound { get; set; }
    public int NewJobs { get; set; }

    public string? CoverageState { get; set; }
    public string? Notes { get; set; }
    public DateTime SearchedAt { get; set; }
}
