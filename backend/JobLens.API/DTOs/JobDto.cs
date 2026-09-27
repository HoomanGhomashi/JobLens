namespace JobLens.API.DTOs;

public class JobDto
{
    public int Id { get; init; }
    public string? Title { get; init; }
    public string? CompanyName { get; init; }
    public string? City { get; init; }
    public string Country { get; init; } = "France";
    public DateTime? PublishedAt { get; init; }
    public string? PublishedAtRaw { get; init; }
    public string? ContractType { get; init; }
    public string? Description { get; init; }
    public int? ExperienceMinYears { get; init; }
    public int? ExperienceMaxYears { get; init; }
    public string? ExperienceRaw { get; init; }
    public bool IsActiveOpportunity { get; init; }
    public string Status { get; init; } = "UNKNOWN";
    public DateTime FirstDiscoveredAt { get; init; }
    public DateTime? LastSeenAt { get; init; }
    public IReadOnlyList<JobSourceDto> Sources { get; init; } = [];
}
