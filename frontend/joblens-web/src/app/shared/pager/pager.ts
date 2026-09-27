import { Component, computed, input, output } from '@angular/core';

@Component({
  selector: 'app-pager',
  templateUrl: './pager.html',
})
export class Pager {
  readonly page = input.required<number>();
  readonly pageSize = input.required<number>();
  readonly totalCount = input.required<number>();

  readonly pageChange = output<number>();

  protected readonly totalPages = computed(() => Math.max(1, Math.ceil(this.totalCount() / this.pageSize())));

  protected readonly rangeStart = computed(() =>
    this.totalCount() === 0 ? 0 : (this.page() - 1) * this.pageSize() + 1,
  );

  protected readonly rangeEnd = computed(() => Math.min(this.page() * this.pageSize(), this.totalCount()));

  protected goTo(page: number): void {
    if (page < 1 || page > this.totalPages() || page === this.page()) {
      return;
    }
    this.pageChange.emit(page);
  }
}
