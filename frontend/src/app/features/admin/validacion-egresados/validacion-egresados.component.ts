import { CommonModule } from '@angular/common';
import { Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../auth/auth.service';
import { Carrera, PerfilEgresado } from './validacion-egresados.model';
import { ValidacionEgresadosService } from './validacion-egresados.service';

@Component({
  selector: 'app-validacion-egresados',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './validacion-egresados.component.html',
  styleUrl: './validacion-egresados.component.scss',
})
export class ValidacionEgresadosComponent {
  readonly pendientes = signal<PerfilEgresado[]>([]);
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly mensaje = signal<string | null>(null);

  private readonly carreras = signal<Carrera[]>([]);
  readonly carrerasPorId = computed(() => new Map(this.carreras().map((c) => [c.id, c.nombre])));

  motivosRechazo: Record<string, string> = {};

  constructor(
    private readonly service: ValidacionEgresadosService,
    private readonly auth: AuthService,
  ) {
    this.service.listarCarreras().subscribe({
      next: (carreras) => this.carreras.set(carreras),
      error: () => {
        /* no bloquea el listado si el catálogo de carreras falla */
      },
    });
  }

  cargar(): void {
    const token = this.auth.token();
    if (!token) {
      this.error.set('Inicia sesión como administrador para consultar las solicitudes.');
      return;
    }

    this.cargando.set(true);
    this.error.set(null);
    this.mensaje.set(null);
    this.service.listarPendientes(token).subscribe({
      next: (pendientes) => {
        this.pendientes.set(pendientes);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar la lista de pendientes. Verifica el token.');
        this.cargando.set(false);
      },
    });
  }

  nombreCarrera(carreraId: string | null): string {
    if (carreraId === null) return '—';
    return this.carrerasPorId().get(carreraId) ?? `#${carreraId}`;
  }

  aprobar(perfil: PerfilEgresado): void {
    this.decidir(perfil, true);
  }

  rechazar(perfil: PerfilEgresado): void {
    const motivo = (this.motivosRechazo[perfil.id] ?? '').trim();
    if (!motivo) {
      this.error.set('Indica el motivo del rechazo antes de continuar.');
      return;
    }
    this.decidir(perfil, false, motivo);
  }

  private decidir(perfil: PerfilEgresado, aprobado: boolean, motivoRechazo?: string): void {
    const token = this.auth.token();
    if (!token) {
      this.error.set('Inicia sesión como administrador para decidir sobre una solicitud.');
      return;
    }

    this.error.set(null);
    this.service.decidir(token, perfil.id, { aprobado, motivo_rechazo: motivoRechazo ?? null }).subscribe({
      next: () => {
        this.pendientes.set(this.pendientes().filter((p) => p.id !== perfil.id));
        this.mensaje.set(
          aprobado
            ? `Egresado ${perfil.nombres} ${perfil.apellidos} aprobado.`
            : `Egresado ${perfil.nombres} ${perfil.apellidos} rechazado.`,
        );
      },
      error: () => this.error.set('No se pudo registrar la decisión.'),
    });
  }
}
