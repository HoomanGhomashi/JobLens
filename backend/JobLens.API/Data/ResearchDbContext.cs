using JobLens.API.Models;
using Microsoft.EntityFrameworkCore;

namespace JobLens.API.Data;

/// <summary>
/// Read-only view over the "research" schema owned by research-engine (Python).
/// This context intentionally maps to tables that already exist in the database —
/// no migrations are generated or applied from here. Do not add write operations
/// against these tables from the API; the research-engine pipeline is the sole writer.
/// </summary>
public class ResearchDbContext(DbContextOptions<ResearchDbContext> options) : DbContext(options)
{
    public DbSet<Company> Companies => Set<Company>();
    public DbSet<Job> Jobs => Set<Job>();
    public DbSet<JobSource> JobSources => Set<JobSource>();
    public DbSet<SearchHistoryRecord> SearchHistory => Set<SearchHistoryRecord>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Company>(entity =>
        {
            entity.ToTable("Companies", schema: "research");
            entity.HasKey(c => c.Id);
        });

        modelBuilder.Entity<Job>(entity =>
        {
            entity.ToTable("Jobs", schema: "research");
            entity.HasKey(j => j.Id);
            entity.HasOne(j => j.Company)
                  .WithMany()
                  .HasForeignKey(j => j.CompanyId)
                  .OnDelete(DeleteBehavior.ClientSetNull);
        });

        modelBuilder.Entity<JobSource>(entity =>
        {
            entity.ToTable("JobSources", schema: "research");
            entity.HasKey(s => s.Id);
            entity.HasOne(s => s.Job)
                  .WithMany(j => j.Sources)
                  .HasForeignKey(s => s.JobId)
                  .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<SearchHistoryRecord>(entity =>
        {
            entity.ToTable("SearchHistory", schema: "research");
            entity.HasKey(s => s.Id);
        });
    }
}
