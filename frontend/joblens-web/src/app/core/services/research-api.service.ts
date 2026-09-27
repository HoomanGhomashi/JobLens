import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  CompanyDto,
  JobDto,
  JobSourceDto,
  OverviewDto,
  PagedResult,
  SearchHistoryDto,
} from '../models/research.models';

// Matches the API's MaxPageSize (ResearchController) — large enough to fetch
// every row in one call for a dashboard of this size, avoiding server-side
// search/filter params entirely: search/filter/pagination happen client-side.
const FETCH_ALL_PAGE_SIZE = 100;

/**
 * Local Mode data source — talks to the real ASP.NET Core API, backed by SQL Server.
 */
@Injectable({ providedIn: 'root' })
export class ResearchApiService {
  private readonly apiBase = environment.apiBaseUrl;

  constructor(private readonly http: HttpClient) {}

  getOverview(): Observable<OverviewDto> {
    return this.http.get<OverviewDto>(`${this.apiBase}/overview`);
  }

  getCompanies(): Observable<CompanyDto[]> {
    return this.http
      .get<PagedResult<CompanyDto>>(`${this.apiBase}/companies`, { params: this.fetchAllParams() })
      .pipe(map((r) => r.items));
  }

  getJobs(): Observable<JobDto[]> {
    return this.http
      .get<PagedResult<JobDto>>(`${this.apiBase}/jobs`, { params: this.fetchAllParams() })
      .pipe(map((r) => r.items));
  }

  getJobSources(): Observable<JobSourceDto[]> {
    return this.http
      .get<PagedResult<JobSourceDto>>(`${this.apiBase}/job-sources`, { params: this.fetchAllParams() })
      .pipe(map((r) => r.items));
  }

  getSearchHistory(): Observable<SearchHistoryDto[]> {
    return this.http
      .get<PagedResult<SearchHistoryDto>>(`${this.apiBase}/search-history`, { params: this.fetchAllParams() })
      .pipe(map((r) => r.items));
  }

  private fetchAllParams(): HttpParams {
    return new HttpParams().set('page', 1).set('pageSize', FETCH_ALL_PAGE_SIZE);
  }
}
