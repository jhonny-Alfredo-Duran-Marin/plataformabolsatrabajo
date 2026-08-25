import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-loading-spinner',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span
      class="spinner"
      [class.spinner--sm]="size === 'sm'"
      [class.spinner--lg]="size === 'lg'"
      [style.border-top-color]="color"
      role="status"
      aria-label="Cargando…"
    ></span>
  `,
  styles: [`
    .spinner {
      display: inline-block;
      border-radius: 50%;
      border: 3px solid rgba(255, 255, 255, 0.3);
      border-top-color: #fff;
      animation: spin 0.7s linear infinite;
      flex-shrink: 0;
      width: 20px;
      height: 20px;
    }
    .spinner--sm { width: 14px; height: 14px; border-width: 2px; }
    .spinner--lg { width: 32px; height: 32px; border-width: 4px; }

    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class LoadingSpinnerComponent {
  /** Tamaño del spinner: 'sm' | 'md' (default) | 'lg' */
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  /** Color del arco superior (por defecto blanco) */
  @Input() color = '#ffffff';
}
