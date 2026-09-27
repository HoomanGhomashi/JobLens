import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { CompanyDto, JobDto, JobSourceDto, OverviewDto, SearchHistoryDto } from '../models/research.models';
import { ResearchApiService } from './research-api.service';
import { DemoDataService } from './demo-data.service';

export type DataMode = 'local' | 'demo';

/**
 * Single entry point the UI depends on. Routes every read to either:
 *   - Local Mode  -> ResearchApiService -> ASP.NET Core API -> SQL Server
 *   - Demo Mode   -> DemoDataService    -> static JSON (public/demo/*.json)
 *
 * Which one is active is decided at build time by `environment.dataMode`
 * (see angular.json's "demo" configuration) — components never branch on it.
 */
@Injectable({ providedIn: 'root' })
export class ResearchDataService {
  readonly mode: DataMode = environment.dataMode;

  constructor(
    private readonly localApi: ResearchApiService,
    private readonly demo: DemoDataService,
  ) {}

  get isDemo(): boolean {
    return this.mode === 'demo';
  }

  getOverview(): Observable<OverviewDto> {
    return this.isDemo ? this.demo.getOverview() : this.localApi.getOverview();
  }

  getCompanies(): Observable<CompanyDto[]> {
    return this.isDemo ? this.demo.getCompanies() : this.localApi.getCompanies();
  }

  getJobs(): Observable<JobDto[]> {
    return this.isDemo ? this.demo.getJobs() : this.localApi.getJobs();
  }

  getJobSources(): Observable<JobSourceDto[]> {
    return this.isDemo ? this.demo.getJobSources() : this.localApi.getJobSources();
  }

  getSearchHistory(): Observable<SearchHistoryDto[]> {
    return this.isDemo ? this.demo.getSearchHistory() : this.localApi.getSearchHistory();
  }
}
