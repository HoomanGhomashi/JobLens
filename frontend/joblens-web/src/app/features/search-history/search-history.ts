import { Component, OnInit, computed, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ResearchDataService } from '../../core/services/research-data.service';
import { SearchHistoryDto } from '../../core/models/research.models';
import { coverageBadgeClass } from '../../shared/badge-styles';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyErrorState } from '../../shared/empty-error-state/empty-error-state';

@Component({
  selector: 'app-search-history',
  imports: [DatePipe, PageHeader, EmptyErrorState],
  templateUrl: './search-history.html',
})
export class SearchHistory implements OnInit {
  protected readonly all = signal<SearchHistoryDto[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly coverageBadgeClass = coverageBadgeClass;

  protected readonly sorted = computed(() =>
    [...this.all()].sort((a, b) => new Date(b.searchedAt).getTime() - new Date(a.searchedAt).getTime()),
  );

  constructor(private readonly api: ResearchDataService) {}

  ngOnInit(): void {
    this.load();
  }

  protected refresh(): void {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getSearchHistory().subscribe({
      next: (items) => {
        this.all.set(items);
        this.loading.set(false);
      },
      error: () => {
        this.error.set("Impossible de charger l'historique.");
        this.loading.set(false);
      },
    });
  }
}
