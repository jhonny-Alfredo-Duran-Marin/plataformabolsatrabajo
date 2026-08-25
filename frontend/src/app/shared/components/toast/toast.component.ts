/**
 * ToastComponent — Renderizador global de notificaciones.
 * Debe incluirse UNA VEZ en app.component.html.
 * Consume ToastService y renderiza las alertas en la esquina superior derecha.
 */
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService, Toast } from '../../../core/services/toast.service';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast-container" role="region" aria-label="Notificaciones" aria-live="polite">
      @for (toast of toastService.toasts(); track toast.id) {
        <div class="toast toast--{{ toast.type }}" (click)="toastService.dismiss(toast.id)">
          <span class="toast__icon">{{ icons[toast.type] }}</span>
          <span class="toast__message">{{ toast.message }}</span>
          <button class="toast__close" aria-label="Cerrar notificación">✕</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      top: 1.25rem;
      right: 1.25rem;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 0.625rem;
      max-width: 360px;
      width: calc(100vw - 2.5rem);
    }

    .toast {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 0.875rem 1rem;
      border-radius: 10px;
      font-size: 0.875rem;
      font-weight: 500;
      line-height: 1.5;
      cursor: pointer;
      animation: slideIn 0.3s cubic-bezier(0.22, 1, 0.36, 1);
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
      transition: opacity 0.2s, transform 0.2s;

      &:hover { opacity: 0.92; }
      &:active { transform: scale(0.98); }
    }

    .toast--success { background: #f0fdf4; border: 1px solid #86efac; color: #166534; }
    .toast--error   { background: #fef2f2; border: 1px solid #fca5a5; color: #991b1b; }
    .toast--warning { background: #fffbeb; border: 1px solid #fcd34d; color: #92400e; }
    .toast--info    { background: #eff6ff; border: 1px solid #93c5fd; color: #1e40af; }

    .toast__icon { font-size: 1rem; flex-shrink: 0; }
    .toast__message { flex: 1; }
    .toast__close {
      background: none; border: none; cursor: pointer;
      font-size: 0.75rem; opacity: 0.6; padding: 0;
      color: inherit; transition: opacity 0.2s;
      &:hover { opacity: 1; }
    }

    @keyframes slideIn {
      from { opacity: 0; transform: translateX(1rem); }
      to   { opacity: 1; transform: translateX(0); }
    }
  `]
})
export class ToastComponent {
  toastService = inject(ToastService);

  readonly icons: Record<string, string> = {
    success: '✅',
    error:   '❌',
    warning: '⚠️',
    info:    'ℹ️',
  };

  identify(_: number, toast: Toast) { return toast.id; }
}
