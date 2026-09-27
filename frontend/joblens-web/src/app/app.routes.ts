import { Routes } from '@angular/router';
import { Overview } from './features/overview/overview';
import { Companies } from './features/companies/companies';
import { Jobs } from './features/jobs/jobs';
import { JobSources } from './features/job-sources/job-sources';
import { SearchHistory } from './features/search-history/search-history';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'overview' },
  { path: 'overview', component: Overview },
  { path: 'companies', component: Companies },
  { path: 'jobs', component: Jobs },
  { path: 'job-sources', component: JobSources },
  { path: 'search-history', component: SearchHistory },
  { path: '**', redirectTo: 'overview' },
];
