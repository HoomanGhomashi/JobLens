namespace JobLens.API.Models;

/// <summary>
/// Maps to research.JobSources (owned by the Python research-engine — read-only from this API).
/// </summary>
public class JobSource
{
    public int Id { get; set; }
    public int JobId { get; set; }
    public Job? Job { get; set; }

    public string? Source { get; set; }
    public string? SourceJobId { get; set; }
    public string? SourceUrl { get; set; }

    public bool UrlVerified { get; set; }
    public bool UrlReliable { get; set; }

    public string? PageTitle { get; set; }
    public string? PageContent { get; set; }

    public DateTime DiscoveredAt { get; set; }
    public DateTime? LastSeenAt { get; set; }
    public DateTime? VerifiedAt { get; set; }
}
