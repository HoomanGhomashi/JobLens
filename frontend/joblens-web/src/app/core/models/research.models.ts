export interface PagedResult<T> {
  items: T[];
  totalCount: number;
  page: number;
  pageSize: number;
}

export interface JobSourceDto {
  id: number;
  jobId: number;
  jobTitle: string | null;
  source: string | null;
  sourceUrl: string | null;
  urlVerified: boolean;
  urlReliable: boolean;
  pageTitle: string | null;
  discoveredAt: string;
  verifiedAt: string | null;
}

export interface JobDto {
  id: number;
  title: string | null;
  companyName: string | null;
  city: string | null;
  country: string;
  publishedAt: string | null;
  publishedAtRaw: string | null;
  contractType: string | null;
  description: string | null;
  experienceMinYears: number | null;
  experienceMaxYears: number | null;
  experienceRaw: string | null;
  isActiveOpportunity: boolean;
  status: string;
  firstDiscoveredAt: string;
  lastSeenAt: string | null;
  sources: JobSourceDto[];
}

export interface CompanyDto {
  id: number;
  name: string;
  domain: string | null;
  website: string | null;
  city: string | null;
  department: string | null;
  companyType: string | null;
  sector: string | null;
  juniorHiringSignal: string;
  hiringHistorySignal: string;
  frenchLanguageSignal: string;
  status: string;
  relevanceReason: string | null;
  firstDiscoveredAt: string | null;
  lastResearchedAt: string | null;
  lastRelevantVacancyAt: string | null;
}

export interface SearchHistoryDto {
  id: number;
  geography: string | null;
  city: string | null;
  department: string | null;
  searchType: string | null;
  queriesUsed: string[];
  sourcesChecked: string[];
  apifyRunId: string | null;
  companiesFound: number;
  newCompanies: number;
  duplicatesFound: number;
  jobsFound: number;
  newJobs: number;
  coverageState: string | null;
  notes: string | null;
  searchedAt: string;
}

export interface OverviewDto {
  companiesCount: number;
  jobsCount: number;
  activeOpportunitiesCount: number;
  jobSourcesCount: number;
  searchHistoryCount: number;
  lastSearchAt: string | null;
  lastCoverageState: string | null;
  recentJobs: JobDto[];
}
