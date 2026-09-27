import { Component, input } from '@angular/core';

@Component({
  selector: 'app-empty-error-state',
  templateUrl: './empty-error-state.html',
})
export class EmptyErrorState {
  readonly kind = input<'empty' | 'error'>('empty');
  readonly title = input.required<string>();
  readonly description = input<string>('');
}
