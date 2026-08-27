/**
 * TimeoutService — Detecta inactividad del usuario y cierra la sesión automáticamente.
 * - Monitorea eventos del DOM: mousemove, keydown, click, scroll, touchstart.
 * - Emite advertencia a los (TIMEOUT - WARNING_LEAD) ms.
 * - Ejecuta logout al llegar al límite de inactividad.
 */
import { Injectable, OnDestroy, inject } from '@angular/core';
import { fromEvent, merge, Subscription, timer } from 'rxjs';
import { switchMap, tap } from 'rxjs/operators';
import { ToastService } from './toast.service';
import { environment } from '../../../environments/environment';

const TIMEOUT_MS = (environment.sessionTimeoutMinutes ?? 15) * 60 * 1000;
const WARNING_LEAD_MS = Math.min(2 * 60 * 1000, TIMEOUT_MS / 2); // Advertencia antes del cierre
const WARNING_TOAST_MS = TIMEOUT_MS - WARNING_LEAD_MS;

/** Eventos del usuario que reinician el contador de inactividad. */
const ACTIVITY_EVENTS = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];

@Injectable({ providedIn: 'root' })
export class TimeoutService implements OnDestroy {
  private toast = inject(ToastService);

  private _sub: Subscription | null = null;
  private _warnSub: Subscription | null = null;
  private _logoutFn: (() => void) | null = null;

  /**
   * Inicia el monitoreo de inactividad.
   * @param logoutFn Callback que ejecuta el logout real (inyectado para evitar dependencia circular con AuthService).
   */
  start(logoutFn: () => void): void {
    this._logoutFn = logoutFn;
    this._clearTimers();

    // Flujo de actividad: cualquier evento reinicia el timer
    const activity$ = merge(
      ...ACTIVITY_EVENTS.map((evt) => fromEvent(document, evt))
    );

    this._sub = activity$
      .pipe(
        // En cada actividad, reinicia los timers
        switchMap(() => this._startTimers())
      )
      .subscribe();

    // Arranque inicial sin esperar al primer evento
    this._startTimers().subscribe();
  }

  stop(): void {
    this._clearTimers();
    this._logoutFn = null;
  }

  private _startTimers() {
    // Timer de advertencia (a los 13 min)
    this._warnSub?.unsubscribe();
    this._warnSub = timer(WARNING_TOAST_MS).subscribe(() => {
      this.toast.warning('Tu sesión expirará en 2 minutos por inactividad.', 10_000);
    });

    // Timer de cierre automático (a los 15 min)
    return timer(TIMEOUT_MS).pipe(
      tap(() => {
        this.toast.info('Tu sesión se cerró por inactividad.');
        this._logoutFn?.();
      })
    );
  }

  private _clearTimers(): void {
    this._sub?.unsubscribe();
    this._warnSub?.unsubscribe();
    this._sub = null;
    this._warnSub = null;
  }

  ngOnDestroy(): void {
    this.stop();
  }
}
