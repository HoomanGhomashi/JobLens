import { Component, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ResearchDataService } from '../../core/services/research-data.service';
import { OverviewDto } from '../../core/models/research.models';
import { contractBadgeClass, activeOpportunityBadgeClass } from '../../shared/badge-styles';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyErrorState } from '../../shared/empty-error-state/empty-error-state';

interface MetricCard {
  label: string;
  value: number;
  description: string;
  icon: string;
  iconClass: string;
  valueClass: string;
}

@Component({
  selector: 'app-overview',
  imports: [RouterLink, DatePipe, PageHeader, EmptyErrorState],
  templateUrl: './overview.html',
})
export class Overview implements OnInit {
  protected readonly data = signal<OverviewDto | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly contractBadgeClass = contractBadgeClass;
  protected readonly activeOpportunityBadgeClass = activeOpportunityBadgeClass;

  constructor(private readonly api: ResearchDataService) {}

  ngOnInit(): void {
    this.load();
  }

  protected refresh(): void {
    this.load();
  }

  protected metrics(d: OverviewDto): MetricCard[] {
    return [
      {
        label: 'Companies',
        value: d.companiesCount,
        description: 'Entreprises identifiées par le research engine',
        icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m-1 4h1m4-8h1m-1 4h1m-1 4h1m-5-8v12',
        iconClass: 'bg-sky-500/10 text-sky-400',
        valueClass: 'text-fg',
      },
      {
        label: 'Jobs',
        value: d.jobsCount,
        description: 'Offres découvertes au total',
        icon: 'M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18a48.108 48.108 0 01-12.756 0c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.653v-2.15a2.25 2.25 0 00-1.5-2.121l-6-2.25a2.25 2.25 0 00-1.5 0l-6 2.25a2.25 2.25 0 00-1.5 2.121v2.15c0 .636.28 1.243.75 1.653m16.5 0a2.243 2.243 0 01-1.72.653l-.653-.05m-14.4 0c.55.048 1.11.08 1.673.096M6 18v-4.25',
        iconClass: 'bg-violet-500/10 text-violet-400',
        valueClass: 'text-fg',
      },
      {
        label: 'Active Opportunities',
        value: d.activeOpportunitiesCount,
        description: 'CDI/CDD récents avec URL vérifiée',
        icon: 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
        iconClass: 'bg-brand-600/10 text-brand-400',
        valueClass: 'text-brand-400',
      },
      {
        label: 'Research Runs',
        value: d.searchHistoryCount,
        description: 'Recherches enregistrées dans SearchHistory',
        icon: 'M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z',
        iconClass: 'bg-amber-500/10 text-amber-400',
        valueClass: 'text-fg',
      },
    ];
  }

  private load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getOverview().subscribe({
      next: (result) => {
        this.data.set(result);
        this.loading.set(false);
      },
      error: () => {
        this.error.set(
          this.api.isDemo
            ? 'Impossible de charger le dataset de démonstration.'
            : "Impossible de charger les données de l'API. Vérifiez que le backend (http://localhost:5020) est démarré.",
        );
        this.loading.set(false);
      },
    });
  }
}
