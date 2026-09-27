import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, combineLatest, map, shareReplay } from 'rxjs';
import {
  CompanyDto,
  JobDto,
  JobSourceDto,
  OverviewDto,
  SearchHistoryDto,
} from '../models/research.models';

/**
 * Demo Mode data source — reads static synthetic JSON from public/demo/*.json.
 * No backend, no SQL Server. Safe to deploy anywhere (e.g. Vercel) as a static site.
 */
@Injectable({ providedIn: 'root' })
export class DemoDataService {
  private readonly http = inject(HttpClient);

  private readonly companies$ = this.http
    .get<CompanyDto[]>('/demo/companies.json')
    .pipe(shareReplay(1));

  private readonly jobs$ = this.http.get<JobDto[]>('/demo/jobs.json').pipe(shareReplay(1));

  private readonly jobSources$ = this.http
    .get<JobSourceDto[]>('/demo/job-sources.json')
    .pipe(shareReplay(1));

  private readonly searchHistory$ = this.http
    .get<SearchHistoryDto[]>('/demo/search-history.json')
    .pipe(shareReplay(1));

  getCompanies(): Observable<CompanyDto[]> {
    return this.companies$;
  }

  getJobs(): Observable<JobDto[]> {
    return this.jobs$;
  }

  getJobSources(): Observable<JobSourceDto[]> {
    return this.jobSources$;
  }

  getSearchHistory(): Observable<SearchHistoryDto[]> {
    return this.searchHistory$;
  }

  getOverview(): Observable<OverviewDto> {
    return combineLatest([this.companies$, this.jobs$, this.jobSources$, this.searchHistory$]).pipe(
      map(([companies, jobs, jobSources, searchHistory]) => {
        const recentJobs = [...jobs]
          .sort((a, b) => new Date(b.firstDiscoveredAt).getTime() - new Date(a.firstDiscoveredAt).getTime())
          .slice(0, 5);

        const lastSearch = [...searchHistory].sort(
          (a, b) => new Date(b.searchedAt).getTime() - new Date(a.searchedAt).getTime(),
        )[0];

        return {
          companiesCount: companies.length,
          jobsCount: jobs.length,
          activeOpportunitiesCount: jobs.filter((j) => j.isActiveOpportunity).length,
          jobSourcesCount: jobSources.length,
          searchHistoryCount: searchHistory.length,
          lastSearchAt: lastSearch?.searchedAt ?? null,
          lastCoverageState: lastSearch?.coverageState ?? null,
          recentJobs,
        } satisfies OverviewDto;
      }),
    );
  }
}
