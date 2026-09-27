import { Component, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ResearchApiService } from '../../core/services/research-api.service';
import { JobDto, PagedResult } from '../../core/models/research.models';
import { activeOpportunityBadgeClass, contractBadgeClass } from '../../shared/badge-styles';
import { Pager } from '../../shared/pager/pager';

const PAGE_SIZE = 10;

@Component({
  selector: 'app-jobs',
  imports: [DatePipe, Pager],
  templateUrl: './jobs.html',
})
export class Jobs implements OnInit {
  protected readonly result = signal<PagedResult<JobDto> | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly page = signal(1);
  protected readonly pageSize = PAGE_SIZE;
  protected readonly expandedId = signal<number | null>(null);

  protected readonly contractBadgeClass = contractBadgeClass;
  protected readonly activeOpportunityBadgeClass = activeOpportunityBadgeClass;

  constructor(private readonly api: ResearchApiService) {}

  ngOnInit(): void {
    this.load();
  }

  protected onPageChange(page: number): void {
    this.page.set(page);
    this.load();
  }

  protected toggleExpand(jobId: number): void {
    this.expandedId.set(this.expandedId() === jobId ? null : jobId);
  }

  private load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getJobs(this.page(), this.pageSize).subscribe({
      next: (result) => {
        this.result.set(result);
        this.loading.set(false);
      },
      error: () => {
        this.error.set("Impossible de charger les offres depuis l'API.");
        this.loading.set(false);
      },
    });
  }
}
