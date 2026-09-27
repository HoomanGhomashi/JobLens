import { Component, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ResearchApiService } from '../../core/services/research-api.service';
import { OverviewDto } from '../../core/models/research.models';
import { contractBadgeClass, coverageBadgeClass, activeOpportunityBadgeClass } from '../../shared/badge-styles';

@Component({
  selector: 'app-overview',
  imports: [RouterLink, DatePipe],
  templateUrl: './overview.html',
})
export class Overview implements OnInit {
  protected readonly data = signal<OverviewDto | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly contractBadgeClass = contractBadgeClass;
  protected readonly coverageBadgeClass = coverageBadgeClass;
  protected readonly activeOpportunityBadgeClass = activeOpportunityBadgeClass;

  constructor(private readonly api: ResearchApiService) {}

  ngOnInit(): void {
    this.api.getOverview().subscribe({
      next: (result) => {
        this.data.set(result);
        this.loading.set(false);
      },
      error: () => {
        this.error.set("Impossible de charger les données de l'API. Vérifiez que le backend (http://localhost:5020) est démarré.");
        this.loading.set(false);
      },
    });
  }
}
