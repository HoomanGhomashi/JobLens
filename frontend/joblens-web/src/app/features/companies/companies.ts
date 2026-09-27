import { Component, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ResearchApiService } from '../../core/services/research-api.service';
import { CompanyDto, PagedResult } from '../../core/models/research.models';
import { hiringSignalBadgeClass, companyStatusBadgeClass } from '../../shared/badge-styles';
import { Pager } from '../../shared/pager/pager';

const PAGE_SIZE = 10;

@Component({
  selector: 'app-companies',
  imports: [DatePipe, Pager],
  templateUrl: './companies.html',
})
export class Companies implements OnInit {
  protected readonly result = signal<PagedResult<CompanyDto> | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly page = signal(1);
  protected readonly pageSize = PAGE_SIZE;

  protected readonly hiringSignalBadgeClass = hiringSignalBadgeClass;
  protected readonly companyStatusBadgeClass = companyStatusBadgeClass;

  constructor(private readonly api: ResearchApiService) {}

  ngOnInit(): void {
    this.load();
  }

  protected onPageChange(page: number): void {
    this.page.set(page);
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getCompanies(this.page(), this.pageSize).subscribe({
      next: (result) => {
        this.result.set(result);
        this.loading.set(false);
      },
      error: () => {
        this.error.set("Impossible de charger les entreprises depuis l'API.");
        this.loading.set(false);
      },
    });
  }
}
