namespace JobLens.API.DTOs;

public class JobSourceDto
{
    public int Id { get; init; }
    public int JobId { get; init; }
    public string? JobTitle { get; init; }
    public string? Source { get; init; }
    public string? SourceUrl { get; init; }
    public bool UrlVerified { get; init; }
    public bool UrlReliable { get; init; }
    public string? PageTitle { get; init; }
    public DateTime DiscoveredAt { get; init; }
    public DateTime? VerifiedAt { get; init; }
}
