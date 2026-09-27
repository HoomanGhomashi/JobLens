namespace JobLens.API.Models;

/// <summary>
/// Maps to research.Jobs (owned by the Python research-engine — read-only from this API).
/// NOTE: there is no CreatedAt/UpdatedAt on this table — only FirstDiscoveredAt / LastSeenAt / ClosedAt.
/// </summary>
public class Job
{
    public int Id { get; set; }
    public int? CompanyId { get; set; }
    public Company? Company { get; set; }

    public string? Title { get; set; }
    public string? City { get; set; }
    public string Country { get; set; } = "France";

    public DateTime? PublishedAt { get; set; }
    public string? PublishedAtRaw { get; set; }
    public int? AgeAtDiscoveryDays { get; set; }

    public string? ContractType { get; set; }

    public string? ExperienceRaw { get; set; }
    public int? ExperienceMinYears { get; set; }
    public int? ExperienceMaxYears { get; set; }

    public string? Technologies { get; set; }
    public string? LanguageRequirement { get; set; }

    public string? Description { get; set; }
    public string? SalaryRaw { get; set; }

    public string MatchResult { get; set; } = "UNKNOWN";
    public string? MatchReason { get; set; }

    public string Status { get; set; } = "UNKNOWN";
    public bool IsActiveOpportunity { get; set; }

    public DateTime FirstDiscoveredAt { get; set; }
    public DateTime? LastSeenAt { get; set; }
    public DateTime? ClosedAt { get; set; }

    public ICollection<JobSource> Sources { get; set; } = new List<JobSource>();
}
