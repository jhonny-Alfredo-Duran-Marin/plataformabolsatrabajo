import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { TimeoutService } from './timeout.service';
import { ToastService } from './toast.service';

const MINUTO = 60 * 1000;

describe('TimeoutService', () => {
  let servicio: TimeoutService;
  let cierres: number;

  beforeEach(() => {
    vi.useFakeTimers();
    TestBed.configureTestingModule({
      providers: [{ provide: ToastService, useValue: { warning: () => undefined, info: () => undefined } }],
    });
    servicio = TestBed.inject(TimeoutService);
    cierres = 0;
  });

  afterEach(() => {
    servicio.stop();
    vi.useRealTimers();
  });

  it('no cierra la sesión mientras el usuario sigue activo', () => {
    servicio.start(() => cierres++);
    // 20 minutos con actividad cada 5: nunca llega a 15 de inactividad.
    for (let i = 0; i < 4; i++) {
      vi.advanceTimersByTime(5 * MINUTO);
      document.dispatchEvent(new Event('click'));
    }
    expect(cierres).toBe(0);
  });

  it('cierra la sesión tras 15 minutos sin actividad', () => {
    servicio.start(() => cierres++);
    vi.advanceTimersByTime(15 * MINUTO);
    expect(cierres).toBe(1);
  });

  it('al detenerlo no cierra ninguna sesión', () => {
    servicio.start(() => cierres++);
    servicio.stop();
    vi.advanceTimersByTime(30 * MINUTO);
    expect(cierres).toBe(0);
  });
});
