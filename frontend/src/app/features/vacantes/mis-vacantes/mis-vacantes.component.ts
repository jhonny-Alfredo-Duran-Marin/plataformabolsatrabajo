import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { JobStatus, Vacante } from '../../../core/models/vacante.models';
import { ToastService } from '../../../core/services/toast.service';
import { VacanteService } from '../../../core/services/vacante.service';

/**
 * Componente para que la empresa gestione y supervise sus vacantes laborales.
 */
@Component({
  selector: 'app-mis-vacantes',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './mis-vacantes.component.html',
  styleUrl: './mis-vacantes.component.scss',
})
export class MisVacantesComponent implements OnInit {
  private readonly vacanteService = inject(VacanteService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  vacantes: Vacante[] = [];
  cargando = false;

  // Filtros y Paginación
  estadoFiltro = '';
  paginaActual = 1;
  totalItems = 0;
  totalPaginas = 1;
  tamanioPagina = 8;

  // Confirmación de eliminación
  vacanteAEliminar: Vacante | null = null;
  eliminando = false;

  readonly pestaniasEstado = [
    { valor: '', label: 'Todas' },
    { valor: 'published', label: 'Publicadas' },
    { valor: 'draft', label: 'Borradores' },
    { valor: 'paused', label: 'Pausadas' },
    { valor: 'closed', label: 'Cerradas' },
  ];

  ngOnInit(): void {
    this.cargarVacantes();
  }

  cargarVacantes(pagina = 1): void {
    this.cargando = true;
    this.paginaActual = pagina;
    this.cdr.markForCheck();

    this.vacanteService
      .listarMisVacantes({
        estado: this.estadoFiltro || undefined,
        page: this.paginaActual,
        page_size: this.tamanioPagina,
      })
      .subscribe({
        next: (resp) => {
          this.vacantes = resp?.items ?? [];
          this.totalItems = resp?.total ?? 0;
          this.totalPaginas = resp?.total_pages ?? 1;
          this.cargando = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('Error al cargar vacantes:', err);
          this.cargando = false;
          this.cdr.markForCheck();
        },
      });
  }

  cambiarFiltroEstado(nuevoEstado: string): void {
    if (this.estadoFiltro === nuevoEstado) return;
    this.estadoFiltro = nuevoEstado;
    this.cargarVacantes(1);
  }

  cambiarEstado(vacanteOrId: Vacante | string, nuevoEstado: JobStatus): void {
    const id = typeof vacanteOrId === 'string' ? vacanteOrId : vacanteOrId.id;
    const vacanteObj = typeof vacanteOrId === 'object' ? vacanteOrId : this.vacantes.find(v => v.id === id);

    this.vacanteService.cambiarEstado(id, nuevoEstado).subscribe({
      next: (vacanteActualizada) => {
        if (vacanteObj) {
          vacanteObj.status = vacanteActualizada.status;
          vacanteObj.published_at = vacanteActualizada.published_at;
        }
        this.toast.success(
          `Estado de la vacante actualizado a "${this.obtenerBadgeTexto(vacanteActualizada.status)}".`
        );
        this.cargarVacantes(this.paginaActual);
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error al cambiar estado:', err);
        this.cdr.markForCheck();
      },
    });
  }

  // ─── Modal de Eliminación ────────────────────────────────────────────────

  abrirModalEliminar(vacante: Vacante): void {
    this.vacanteAEliminar = vacante;
    this.cdr.markForCheck();
  }

  cancelarEliminar(): void {
    this.vacanteAEliminar = null;
    this.cdr.markForCheck();
  }

  confirmarEliminar(): void {
    if (!this.vacanteAEliminar) return;

    this.eliminando = true;
    const id = this.vacanteAEliminar.id;
    this.cdr.markForCheck();

    this.vacanteService.eliminarVacante(id).subscribe({
      next: () => {
        this.eliminando = false;
        this.toast.success('Vacante eliminada correctamente.');
        this.vacanteAEliminar = null;
        this.cargarVacantes(this.paginaActual);
        this.cdr.markForCheck();
      },
      error: () => {
        this.eliminando = false;
        this.cdr.markForCheck();
      },
    });
  }

  // ─── Helpers Visuales ────────────────────────────────────────────────────

  obtenerBadgeClase(estado: string): string {
    switch (estado) {
      case 'published':
        return 'badge--published';
      case 'draft':
        return 'badge--draft';
      case 'paused':
        return 'badge--paused';
      case 'closed':
      case 'archived':
        return 'badge--closed';
      case 'rejected':
        return 'badge--rejected';
      case 'pending_review':
        return 'badge--pending';
      default:
        return 'badge--default';
    }
  }

  obtenerBadgeTexto(estado: string): string {
    switch (estado) {
      case 'published':
        return 'Publicada';
      case 'draft':
        return 'Borrador';
      case 'paused':
        return 'Pausada';
      case 'closed':
        return 'Cerrada';
      case 'rejected':
        return 'Rechazada';
      case 'pending_review':
        return 'En Revisión';
      case 'archived':
        return 'Archivada';
      default:
        return estado;
    }
  }

  obtenerModalidadTexto(mod?: string | null): string {
    switch (mod) {
      case 'onsite':
        return 'Presencial';
      case 'hybrid':
        return 'Híbrido';
      case 'remote':
        return 'Remoto';
      default:
        return 'No especificada';
    }
  }
}
