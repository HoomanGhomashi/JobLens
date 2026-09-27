namespace JobLens.API.DTOs;

public class CompanyDto
{
    public int Id { get; init; }
    public string Name { get; init; } = string.Empty;
    public string? Domain { get; init; }
    public string? Website { get; init; }
    public string? City { get; init; }
    public string? Department { get; init; }
    public string? CompanyType { get; init; }
    public string? Sector { get; init; }
    public string JuniorHiringSignal { get; init; } = "UNKNOWN";
    public string HiringHistorySignal { get; init; } = "UNKNOWN";
    public string FrenchLanguageSignal { get; init; } = "UNKNOWN";
    public string Status { get; init; } = "MONITOR";
    public string? RelevanceReason { get; init; }
    public DateTime? FirstDiscoveredAt { get; init; }
    public DateTime? LastResearchedAt { get; init; }
    public DateTime? LastRelevantVacancyAt { get; init; }
}
