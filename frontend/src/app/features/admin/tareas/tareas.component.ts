import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ToastService } from '../../../core/services/toast.service';
import {
  Corrida,
  EstadoCorrida,
  PanelTareas,
  TareaAutomatica,
  TareasService,
} from './tareas.service';

const ETIQUETA_ESTADO: Record<EstadoCorrida, string> = {
  running: 'En curso',
  success: 'Correcta',
  failure: 'Con error',
};

const ICONO_TAREA: Record<string, string> = {
  respaldo_diario: '💾',
  cierre_vacantes: '⏰',
  boletin_ofertas: '📬',
  recordatorios: '🔔',
};

/** Procesos que la plataforma corre sola todos los días, con su historial. */
@Component({
  selector: 'app-tareas',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './tareas.component.html',
  styleUrl: './tareas.component.scss',
})
export class TareasComponent implements OnInit {
  private readonly servicio = inject(TareasService);
  private readonly toast = inject(ToastService);

  readonly etiquetaEstado = ETIQUETA_ESTADO;
  readonly panel = signal<PanelTareas | null>(null);
  readonly cargando = signal(true);
  readonly error = signal('');
  readonly ejecutando = signal<string | null>(null);
  readonly abiertas = signal<Set<string>>(new Set());

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.servicio.listar().subscribe({
      next: (panel) => {
        this.panel.set(panel);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(
          typeof err.error?.detail === 'string'
            ? err.error.detail
            : 'No se pudieron cargar las tareas.',
        );
        this.cargando.set(false);
      },
    });
  }

  ejecutar(tarea: TareaAutomatica): void {
    if (this.ejecutando()) return;
    this.ejecutando.set(tarea.clave);
    this.servicio.ejecutar(tarea.clave).subscribe({
      next: (corrida) => {
        this.ejecutando.set(null);
        if (corrida.estado === 'success')
          this.toast.success(corrida.resumen ?? `${tarea.nombre}: listo.`);
        else this.toast.error(corrida.resumen ?? `${tarea.nombre} terminó con error.`);
        this.cargar();
      },
      error: (err: HttpErrorResponse) => {
        this.ejecutando.set(null);
        this.toast.error(
          typeof err.error?.detail === 'string'
            ? err.error.detail
            : 'No se pudo ejecutar la tarea.',
        );
      },
    });
  }

  alternarHistorial(clave: string): void {
    this.abiertas.update((actuales) => {
      const nuevas = new Set(actuales);
      if (!nuevas.delete(clave)) nuevas.add(clave);
      return nuevas;
    });
  }

  icono(clave: string): string {
    return ICONO_TAREA[clave] ?? '⚙️';
  }

  fecha(valor: string | null): string {
    if (!valor) return '—';
    return new Date(valor).toLocaleString('es-BO', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  duracion(c: Corrida): string {
    if (!c.fin) return '';
    const segundos = Math.max(
      0,
      Math.round((new Date(c.fin).getTime() - new Date(c.inicio).getTime()) / 1000),
    );
    return segundos < 60 ? `${segundos} s` : `${Math.floor(segundos / 60)} min ${segundos % 60} s`;
  }

  origen(c: Corrida): string {
    return c.disparador === 'automatico' ? 'Automática' : `Manual${c.autor ? ' · ' + c.autor : ''}`;
  }
}
