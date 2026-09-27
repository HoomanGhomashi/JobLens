namespace JobLens.API.Models;

/// <summary>
/// Maps to research.Companies (owned by the Python research-engine — read-only from this API).
/// </summary>
public class Company
{
    public int Id { get; set; }

    public string Name { get; set; } = string.Empty;
    public string? NormalizedName { get; set; }
    public string? Domain { get; set; }
    public string? Website { get; set; }
    public string? CareersUrl { get; set; }

    public string? City { get; set; }
    public string? Department { get; set; }
    public string Country { get; set; } = "France";

    public string? CompanyType { get; set; }
    public string? Sector { get; set; }

    public string? TechnologiesObserved { get; set; }
    public string? DeveloperRolesObserved { get; set; }

    public string JuniorHiringSignal { get; set; } = "UNKNOWN";
    public string HiringHistorySignal { get; set; } = "UNKNOWN";
    public string FrenchLanguageSignal { get; set; } = "UNKNOWN";

    public bool? AcceptsSpontaneous { get; set; }

    public string Status { get; set; } = "MONITOR";
    public string? RelevanceReason { get; set; }
    public string? SourceUrls { get; set; }
    public string? Notes { get; set; }

    public DateTime? FirstDiscoveredAt { get; set; }
    public DateTime? LastResearchedAt { get; set; }
    public DateTime? LastJobCheckAt { get; set; }
    public DateTime? LastRelevantVacancyAt { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}
