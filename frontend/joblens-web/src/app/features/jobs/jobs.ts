import { Component, OnInit, computed, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ResearchDataService } from '../../core/services/research-data.service';
import { JobDto } from '../../core/models/research.models';
import { activeOpportunityBadgeClass, contractBadgeClass } from '../../shared/badge-styles';
import { Pager } from '../../shared/pager/pager';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyErrorState } from '../../shared/empty-error-state/empty-error-state';
import { matchesSearch, paginate } from '../../shared/list-utils';

const PAGE_SIZE = 8;
type ActiveFilter = 'all' | 'active' | 'inactive';

@Component({
  selector: 'app-jobs',
  imports: [DatePipe, FormsModule, Pager, PageHeader, EmptyErrorState],
  templateUrl: './jobs.html',
})
export class Jobs implements OnInit {
  protected readonly all = signal<JobDto[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly page = signal(1);
  protected readonly search = signal('');
  protected readonly contractFilter = signal<string>('all');
  protected readonly activeFilter = signal<ActiveFilter>('all');
  protected readonly expandedId = signal<number | null>(null);
  protected readonly pageSize = PAGE_SIZE;

  protected readonly contractBadgeClass = contractBadgeClass;
  protected readonly activeOpportunityBadgeClass = activeOpportunityBadgeClass;

  protected readonly activeFilterOptions: { value: ActiveFilter; label: string }[] = [
    { value: 'all', label: 'Toutes' },
    { value: 'active', label: 'Actives' },
    { value: 'inactive', label: 'Inactives' },
  ];

  protected readonly contractOptions = computed(() => {
    const set = new Set(this.all().map((j) => j.contractType).filter((c): c is string => !!c));
    return ['all', ...Array.from(set).sort()];
  });

  protected readonly filtered = computed(() => {
    const contract = this.contractFilter();
    const active = this.activeFilter();
    return this.all().filter((j) => {
      if (contract !== 'all' && j.contractType !== contract) return false;
      if (active === 'active' && !j.isActiveOpportunity) return false;
      if (active === 'inactive' && j.isActiveOpportunity) return false;
      return matchesSearch(this.search(), j.title, j.companyName, j.city);
    });
  });

  protected readonly pageItems = computed(() => paginate(this.filtered(), this.page(), this.pageSize));

  constructor(private readonly api: ResearchDataService) {}

  ngOnInit(): void {
    this.load();
  }

  protected onSearchChange(term: string): void {
    this.search.set(term);
    this.page.set(1);
  }

  protected onContractChange(value: string): void {
    this.contractFilter.set(value);
    this.page.set(1);
  }

  protected onActiveFilterChange(value: ActiveFilter): void {
    this.activeFilter.set(value);
    this.page.set(1);
  }

  protected onPageChange(page: number): void {
    this.page.set(page);
  }

  protected toggleExpand(jobId: number): void {
    this.expandedId.set(this.expandedId() === jobId ? null : jobId);
  }

  protected refresh(): void {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getJobs().subscribe({
      next: (items) => {
        this.all.set(items);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Impossible de charger les offres.');
        this.loading.set(false);
      },
    });
  }
}
