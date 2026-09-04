import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ToastService } from '../../../core/services/toast.service';
import {
  DetallePostulacion,
  FiltroPostulaciones,
  PostulacionItem,
  ResumenPostulaciones,
} from '../postulaciones.models';
import { PostulacionesService } from '../postulaciones.service';

@Component({
  selector: 'app-mis-postulaciones',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './mis-postulaciones.component.html',
  styleUrl: './mis-postulaciones.component.scss',
})
export class MisPostulacionesComponent implements OnInit {
  private readonly postulacionesService = inject(PostulacionesService);
  private readonly toast = inject(ToastService);

  // Estados reactivos
  loading = signal<boolean>(true);
  resumen = signal<ResumenPostulaciones | null>(null);
  postulaciones = signal<PostulacionItem[]>([]);

  // Filtros
  busqueda = '';
  estadoSeleccionado = '';
  fechaDesde = '';
  fechaHasta = '';

  // Modal de Detalle / Timeline
  modalDetalleAbierto = signal<boolean>(false);
  cargandoDetalle = signal<boolean>(false);
  detalleSeleccionado = signal<DetallePostulacion | null>(null);
  pestanaActiva = signal<'seguimiento' | 'vacante'>('seguimiento');

  // Modal de Retiro de Postulación
  modalRetirarAbierto = signal<boolean>(false);
  postulacionARetirar = signal<PostulacionItem | null>(null);
  motivoRetiro = '';
  retirando = signal<boolean>(false);

  // Opciones de estados
  readonly opcionesEstados = [
    { valor: '', label: 'Todos los estados' },
    { valor: 'applied', label: 'Postulado' },
    { valor: 'screening', label: 'En revisión' },
    { valor: 'shortlisted', label: 'Preseleccionado' },
    { valor: 'interview', label: 'En entrevista' },
    { valor: 'assessment', label: 'En pruebas' },
    { valor: 'offer', label: 'Oferta recibida' },
    { valor: 'hired', label: 'Contratado' },
    { valor: 'rejected', label: 'No seleccionado / Rechazado' },
    { valor: 'withdrawn', label: 'Postulación retirada' },
  ];

  ngOnInit(): void {
    this.cargarPostulaciones();
  }

  cargarPostulaciones(): void {
    this.loading.set(true);
    const filtros: FiltroPostulaciones = {};
    if (this.estadoSeleccionado) filtros.estado = this.estadoSeleccionado;
    if (this.fechaDesde) filtros.fecha_desde = this.fechaDesde;
    if (this.fechaHasta) filtros.fecha_hasta = this.fechaHasta;
    if (this.busqueda.trim()) filtros.busqueda = this.busqueda.trim();

    this.postulacionesService.obtenerMisPostulaciones(filtros).subscribe({
      next: (data) => {
        this.resumen.set(data);
        this.postulaciones.set(data.postulaciones);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.toast.error('Error al cargar tus postulaciones. Intenta nuevamente.');
      },
    });
  }

  onFiltroChange(): void {
    this.cargarPostulaciones();
  }

  limpiarFiltros(): void {
    this.busqueda = '';
    this.estadoSeleccionado = '';
    this.fechaDesde = '';
    this.fechaHasta = '';
    this.cargarPostulaciones();
  }

  abrirDetalle(postulacion: PostulacionItem, pestana: 'seguimiento' | 'vacante' = 'seguimiento'): void {
    this.modalDetalleAbierto.set(true);
    this.cargandoDetalle.set(true);
    this.pestanaActiva.set(pestana);
    this.detalleSeleccionado.set(null);

    this.postulacionesService.obtenerDetalle(postulacion.id).subscribe({
      next: (detalle) => {
        this.detalleSeleccionado.set(detalle);
        this.cargandoDetalle.set(false);
      },
      error: (err) => {
        this.cargandoDetalle.set(false);
        this.toast.error('No se pudo cargar el detalle de la postulación.');
      },
    });
  }

  cerrarModalDetalle(): void {
    this.modalDetalleAbierto.set(false);
    this.detalleSeleccionado.set(null);
  }

  abrirModalRetirar(postulacion: PostulacionItem, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.postulacionARetirar.set(postulacion);
    this.motivoRetiro = '';
    this.modalRetirarAbierto.set(true);
  }

  cerrarModalRetirar(): void {
    this.modalRetirarAbierto.set(false);
    this.postulacionARetirar.set(null);
    this.motivoRetiro = '';
  }

  confirmarRetiro(): void {
    const post = this.postulacionARetirar();
    if (!post) return;

    this.retirando.set(true);
    this.postulacionesService.retirarPostulacion(post.id, this.motivoRetiro).subscribe({
      next: (actualizada) => {
        this.retirando.set(false);
        this.toast.success('Postulación retirada exitosamente.');
        this.cerrarModalRetirar();
        // Si el modal de detalle estaba abierto para esta postulación, refrescarlo
        if (this.detalleSeleccionado()?.postulacion.id === post.id) {
          this.abrirDetalle(actualizada, this.pestanaActiva());
        }
        this.cargarPostulaciones();
      },
      error: (err) => {
        this.retirando.set(false);
        const msg = err?.error?.detail || 'No se pudo retirar la postulación.';
        this.toast.error(msg);
      },
    });
  }

  formatearFecha(fechaStr: string | null | undefined): string {
    if (!fechaStr) return '—';
    try {
      const fecha = new Date(fechaStr);
      return fecha.toLocaleDateString('es-BO', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return fechaStr;
    }
  }

  formatearFechaHora(fechaStr: string | null | undefined): string {
    if (!fechaStr) return '—';
    try {
      const fecha = new Date(fechaStr);
      return fecha.toLocaleString('es-BO', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return fechaStr;
    }
  }

  getBadgeClass(color: string): string {
    switch (color) {
      case 'blue':
        return 'badge--blue';
      case 'yellow':
        return 'badge--yellow';
      case 'purple':
        return 'badge--purple';
      case 'indigo':
        return 'badge--indigo';
      case 'cyan':
        return 'badge--cyan';
      case 'emerald':
      case 'green':
        return 'badge--green';
      case 'red':
        return 'badge--red';
      default:
        return 'badge--gray';
    }
  }

  getStepStatus(paso: number, estadoActual: string): 'completado' | 'actual' | 'pendiente' | 'rechazado' {
    if (estadoActual === 'rejected') {
      return 'rechazado';
    }
    if (estadoActual === 'withdrawn') {
      return 'pendiente';
    }

    const mapaOrden: Record<string, number> = {
      applied: 1,
      screening: 2,
      in_review: 2,
      shortlisted: 3,
      interview: 4,
      assessment: 5,
      offer: 6,
      hired: 7,
    };

    const nivelActual = mapaOrden[estadoActual] || 1;
    if (paso < nivelActual) return 'completado';
    if (paso === nivelActual) return 'actual';
    return 'pendiente';
  }
}
