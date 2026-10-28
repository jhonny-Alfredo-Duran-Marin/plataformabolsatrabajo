import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, OnInit, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Notificacion } from '../../../core/models/notificacion.models';
import { NotificacionService } from '../../../core/services/notificacion.service';
import { AuthService } from '../../../features/auth/auth.service';

@Component({
  selector: 'app-notificaciones-campana',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './notificaciones-campana.component.html',
  styleUrl: './notificaciones-campana.component.scss',
})
export class NotificacionesCampanaComponent implements OnInit {
  private readonly notifService = inject(NotificacionService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly elementRef = inject(ElementRef);

  // Signals: la app no usa zone.js, así que un campo común no repinta al llegar la respuesta.
  readonly isOpen = signal(false);
  readonly isLoading = signal(false);
  readonly notificaciones = signal<Notificacion[]>([]);

  readonly noLeidas = this.notifService.noLeidasCount;

  ngOnInit(): void {
    if (this.auth.estaAutenticado()) {
      this.notifService.actualizarContador();
    }
  }

  toggleDropdown(): void {
    this.isOpen.update((abierto) => !abierto);
    if (this.isOpen()) {
      this.cargarNotificaciones();
    }
  }

  cargarNotificaciones(): void {
    this.isLoading.set(true);
    this.notifService.listarNotificaciones(8, 0).subscribe({
      next: (res) => {
        this.notificaciones.set(res.items);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      },
    });
  }

  onNotificacionClick(notif: Notificacion): void {
    if (!notif.leida) {
      this.notifService.marcarComoLeida(notif.id).subscribe({
        next: () => {
          const ahora = new Date().toISOString();
          this.notificaciones.update((lista) =>
            lista.map((n) => (n.id === notif.id ? { ...n, leida: true, read_at: ahora } : n)),
          );
        },
      });
    }

    this.isOpen.set(false);
    if (notif.link) {
      this.router.navigateByUrl(notif.link);
    }
  }

  marcarTodasLeidas(event: Event): void {
    event.stopPropagation();
    this.notifService.marcarTodasComoLeidas().subscribe({
      next: () => {
        const ahora = new Date().toISOString();
        this.notificaciones.update((lista) => lista.map((n) => ({ ...n, leida: true, read_at: n.read_at ?? ahora })));
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
      case 'encuesta_laboral':
        return '📋';
      default:
        return '🔔';
    }
  }

  @HostListener('document:click', ['$event'])
  onClickOutside(event: Event): void {
    if (!this.elementRef.nativeElement.contains(event.target)) {
      this.isOpen.set(false);
    }
  }
}
