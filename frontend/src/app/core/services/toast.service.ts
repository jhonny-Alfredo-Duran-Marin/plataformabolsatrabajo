/**
 * ToastService — Notificaciones globales reactivas (tipo snackbar/toast).
 * Los componentes inyectan este servicio para emitir mensajes.
 * El componente <app-toast> los consume y renderiza.
 */
import { Injectable, signal } from '@angular/core';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: number;
  type: ToastType;
  message: string;
  duration: number;
}

@Injectable({ providedIn: 'root' })
export class ToastService {
  private _counter = 0;

  /** Lista reactiva de toasts activos. */
  readonly toasts = signal<Toast[]>([]);

  show(message: string, type: ToastType = 'info', duration = 4000): void {
    const id = ++this._counter;
    this.toasts.update((list) => [...list, { id, type, message, duration }]);

    // Eliminar automáticamente tras la duración
    setTimeout(() => this.dismiss(id), duration);
  }

  success(message: string, duration = 4000): void { this.show(message, 'success', duration); }
  error(message: string, duration = 5000):   void { this.show(message, 'error',   duration); }
  warning(message: string, duration = 5000): void { this.show(message, 'warning', duration); }
  info(message: string, duration = 4000):    void { this.show(message, 'info',    duration); }

  dismiss(id: number): void {
    this.toasts.update((list) => list.filter((t) => t.id !== id));
  }

  dismissAll(): void {
    this.toasts.set([]);
  }
}
