import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Notificacion, PreferenciasNotificacion } from '../../../core/models/notificacion.models';
import { NotificacionService } from '../../../core/services/notificacion.service';
import { PushService } from '../../../core/services/push.service';
import { AuthService } from '../../auth/auth.service';

@Component({
  selector: 'app-notificaciones-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './notificaciones-panel.component.html',
  styleUrl: './notificaciones-panel.component.scss',
})
export class NotificacionesPanelComponent implements OnInit {
  private readonly notifService = inject(NotificacionService);
  readonly push = inject(PushService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  tabActiva: 'historial' | 'preferencias' = 'historial';
  filtroActual: 'todas' | 'no_leidas' = 'todas';

  // Historial
  notificaciones: Notificacion[] = [];
  total = 0;
  noLeidas = 0;
  isLoadingHistorial = false;

  // Preferencias
  preferencias: PreferenciasNotificacion = {
    email_notifications: true,
    push_enabled: true,
    in_app_enabled: true,
    notify_stage_changes: true,
    notify_job_matches: true,
    notify_interview_events: true,
    notify_messages: true,
  };
  isLoadingPreferencias = false;
  isSavingPreferencias = false;
  activandoPush = false;
  probandoPush = false;

  // Toast / Mensajes
  mensajeExito: string | null = null;
  mensajeError: string | null = null;

  ngOnInit(): void {
    if (!this.auth.estaAutenticado()) {
      this.router.navigate(['/auth/login']);
      return;
    }
    this.cargarHistorial();
    this.cargarPreferencias();
  }

  /** Encender "push" también registra este navegador (pide el permiso si hace falta). */
  async togglePushPermiso(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    this.preferencias.push_enabled = input.checked;
    if (input.checked && this.push.estado() !== 'activo') {
      await this.activarPushEnNavegador();
    }
  }

  async activarPushEnNavegador(): Promise<void> {
    this.activandoPush = true;
    const ok = await this.push.activar();
    this.activandoPush = false;
    if (ok) {
      this.mostrarMensaje('Listo: este navegador va a recibir los avisos aunque EGRESA esté cerrada.');
    } else if (this.push.estado() === 'bloqueado') {
      this.mostrarMensaje('El navegador tiene bloqueados los avisos de este sitio. Habilitalos desde el candado de la barra de direcciones.', true);
    } else if (this.push.estado() !== 'sin-permiso') {
      this.mostrarMensaje('No se pudieron activar los avisos en este navegador. Intentá de nuevo.', true);
    }
  }

  /** Envía un push real desde el servidor a los dispositivos registrados de la cuenta. */
  probarNotificacionPush(): void {
    this.probandoPush = true;
    this.notifService
      .probarPushFCM('Prueba de avisos de EGRESA', 'Si ves esto, los avisos push funcionan en este dispositivo.')
      .subscribe({
        next: (r: { enviados?: number; mensaje?: string }) => {
          this.probandoPush = false;
          if (r.enviados) {
            this.mostrarMensaje(`Aviso de prueba enviado a ${r.enviados} dispositivo(s).`);
          } else {
            this.mostrarMensaje(r.mensaje || 'No hay dispositivos registrados para recibir avisos.', true);
          }
        },
        error: () => {
          this.probandoPush = false;
          this.mostrarMensaje('No se pudo enviar el aviso de prueba.', true);
        },
      });
  }

  cargarHistorial(): void {
    this.isLoadingHistorial = true;
    const soloNoLeidas = this.filtroActual === 'no_leidas';
    this.notifService.listarNotificaciones(50, 0, soloNoLeidas).subscribe({
      next: (res) => {
        this.notificaciones = res.items;
        this.total = res.total;
        this.noLeidas = res.no_leidas;
        this.isLoadingHistorial = false;
      },
      error: () => {
        this.isLoadingHistorial = false;
        this.mostrarMensaje('Error al cargar el historial de notificaciones.', true);
      },
    });
  }

  cambiarFiltro(filtro: 'todas' | 'no_leidas'): void {
    this.filtroActual = filtro;
    this.cargarHistorial();
  }

  marcarComoLeida(notif: Notificacion): void {
    if (notif.leida) return;
    this.notifService.marcarComoLeida(notif.id).subscribe({
      next: () => {
        notif.leida = true;
        notif.read_at = new Date().toISOString();
        this.noLeidas = Math.max(0, this.noLeidas - 1);
      },
    });
  }

  marcarTodasComoLeidas(): void {
    this.notifService.marcarTodasComoLeidas().subscribe({
      next: () => {
        this.notificaciones.forEach((n) => {
          n.leida = true;
          n.read_at = new Date().toISOString();
        });
        this.noLeidas = 0;
        this.mostrarMensaje('Todas las notificaciones fueron marcadas como leídas.');
      },
    });
  }

  eliminarNotificacion(notif: Notificacion, event: Event): void {
    event.stopPropagation();
    this.notifService.eliminarNotificacion(notif.id).subscribe({
      next: () => {
        this.notificaciones = this.notificaciones.filter((n) => n.id !== notif.id);
        this.total = Math.max(0, this.total - 1);
        if (!notif.leida) {
          this.noLeidas = Math.max(0, this.noLeidas - 1);
        }
        this.mostrarMensaje('Notificación eliminada.');
      },
    });
  }

  navegarNotificacion(notif: Notificacion): void {
    this.marcarComoLeida(notif);
    if (notif.link) {
      this.router.navigateByUrl(notif.link);
    }
  }

  // --- PREFERENCIAS ---
  cargarPreferencias(): void {
    this.isLoadingPreferencias = true;
    this.notifService.obtenerPreferencias().subscribe({
      next: (p) => {
        this.preferencias = p;
        this.isLoadingPreferencias = false;
      },
      error: () => {
        this.isLoadingPreferencias = false;
      },
    });
  }

  guardarPreferencias(): void {
    this.isSavingPreferencias = true;
    this.notifService.actualizarPreferencias(this.preferencias).subscribe({
      next: (p) => {
        this.preferencias = p;
        this.isSavingPreferencias = false;
        this.mostrarMensaje('Preferencias de notificación guardadas exitosamente.');
      },
      error: () => {
        this.isSavingPreferencias = false;
        this.mostrarMensaje('No se pudieron guardar las preferencias.', true);
      },
    });
  }

  getIconoTipo(tipo: string): string {
    switch (tipo) {
      case 'stage_change':
        return '📈';
      case 'job_match':
        return '✨';
      case 'vacante_por_cerrar':
      case 'recordatorio_vacante':
        return '⏳';
      case 'vacante_cerrada':
        return '🔒';
      case 'interview_scheduled':
      case 'interview_status':
      case 'interview_reminder':
        return '📅';
      case 'message_received':
        return '💬';
      default:
        return '🔔';
    }
  }

  mostrarMensaje(msg: string, isError = false): void {
    if (isError) {
      this.mensajeError = msg;
      setTimeout(() => (this.mensajeError = null), 4000);
    } else {
      this.mensajeExito = msg;
      setTimeout(() => (this.mensajeExito = null), 4000);
    }
  }
}
