import { Component, input, output } from '@angular/core';
import { ResearchDataService } from '../../core/services/research-data.service';

@Component({
  selector: 'app-page-header',
  templateUrl: './page-header.html',
})
export class PageHeader {
  readonly title = input.required<string>();
  readonly description = input<string>('');
  readonly showRefresh = input(false);
  readonly refresh = output<void>();

  constructor(protected readonly data: ResearchDataService) {}
}
