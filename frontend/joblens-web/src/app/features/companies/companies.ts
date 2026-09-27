import { Component, OnInit, computed, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ResearchDataService } from '../../core/services/research-data.service';
import { CompanyDto } from '../../core/models/research.models';
import { hiringSignalBadgeClass, companyStatusBadgeClass } from '../../shared/badge-styles';
import { Pager } from '../../shared/pager/pager';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyErrorState } from '../../shared/empty-error-state/empty-error-state';
import { matchesSearch, paginate } from '../../shared/list-utils';

const PAGE_SIZE = 9;

@Component({
  selector: 'app-companies',
  imports: [DatePipe, FormsModule, Pager, PageHeader, EmptyErrorState],
  templateUrl: './companies.html',
})
export class Companies implements OnInit {
  protected readonly all = signal<CompanyDto[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly page = signal(1);
  protected readonly search = signal('');
  protected readonly pageSize = PAGE_SIZE;

  protected readonly hiringSignalBadgeClass = hiringSignalBadgeClass;
  protected readonly companyStatusBadgeClass = companyStatusBadgeClass;

  protected readonly filtered = computed(() =>
    this.all().filter((c) => matchesSearch(this.search(), c.name, c.domain, c.city, c.sector)),
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
    this.api.getCompanies().subscribe({
      next: (items) => {
        this.all.set(items);
        this.loading.set(false);
      },
      error: () => {
        this.error.set("Impossible de charger les entreprises.");
        this.loading.set(false);
      },
    });
  }
}
