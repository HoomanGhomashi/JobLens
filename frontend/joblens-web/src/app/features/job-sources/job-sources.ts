import { Component, OnInit, computed, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ResearchDataService } from '../../core/services/research-data.service';
import { JobSourceDto } from '../../core/models/research.models';
import { urlFlagBadgeClass } from '../../shared/badge-styles';
import { Pager } from '../../shared/pager/pager';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyErrorState } from '../../shared/empty-error-state/empty-error-state';
import { matchesSearch, paginate } from '../../shared/list-utils';

const PAGE_SIZE = 10;

@Component({
  selector: 'app-job-sources',
  imports: [DatePipe, FormsModule, Pager, PageHeader, EmptyErrorState],
  templateUrl: './job-sources.html',
})
export class JobSources implements OnInit {
  protected readonly all = signal<JobSourceDto[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly page = signal(1);
  protected readonly search = signal('');
  protected readonly pageSize = PAGE_SIZE;

  protected readonly urlFlagBadgeClass = urlFlagBadgeClass;

  protected readonly filtered = computed(() =>
    this.all().filter((s) => matchesSearch(this.search(), s.jobTitle, s.source, s.sourceUrl)),
  );

  protected readonly pageItems = computed(() => paginate(this.filtered(), this.page(), this.pageSize));

  constructor(private readonly api: ResearchDataService) {}

  ngOnInit(): void {
    this.load();
  }

  protected onSearchChange(term: string): void {
    this.search.set(term);
    this.page.set(1);
  }

  protected onPageChange(page: number): void {
    this.page.set(page);
  }

  protected refresh(): void {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getJobSources().subscribe({
      next: (items) => {
        this.all.set(items);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Impossible de charger les sources.');
        this.loading.set(false);
      },
    });
  }
}
