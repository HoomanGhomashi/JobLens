import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  CompanyDto,
  JobDto,
  JobSourceDto,
  OverviewDto,
  PagedResult,
  SearchHistoryDto,
} from '../models/research.models';

// Local development only — matches backend/JobLens.API's http launch profile.
const API_BASE = 'http://localhost:5020/api/research';

@Injectable({ providedIn: 'root' })
export class ResearchApiService {
  constructor(private readonly http: HttpClient) {}

  getOverview(): Observable<OverviewDto> {
    return this.http.get<OverviewDto>(`${API_BASE}/overview`);
  }

  getCompanies(page: number, pageSize: number): Observable<PagedResult<CompanyDto>> {
    return this.http.get<PagedResult<CompanyDto>>(`${API_BASE}/companies`, {
      params: this.pagingParams(page, pageSize),
    });
  }

  getJobs(page: number, pageSize: number): Observable<PagedResult<JobDto>> {
    return this.http.get<PagedResult<JobDto>>(`${API_BASE}/jobs`, {
      params: this.pagingParams(page, pageSize),
    });
  }

  getJobSources(page: number, pageSize: number): Observable<PagedResult<JobSourceDto>> {
    return this.http.get<PagedResult<JobSourceDto>>(`${API_BASE}/job-sources`, {
      params: this.pagingParams(page, pageSize),
    });
  }

  getSearchHistory(page: number, pageSize: number): Observable<PagedResult<SearchHistoryDto>> {
    return this.http.get<PagedResult<SearchHistoryDto>>(`${API_BASE}/search-history`, {
      params: this.pagingParams(page, pageSize),
    });
  }

  private pagingParams(page: number, pageSize: number): HttpParams {
    return new HttpParams().set('page', page).set('pageSize', pageSize);
  }
}
