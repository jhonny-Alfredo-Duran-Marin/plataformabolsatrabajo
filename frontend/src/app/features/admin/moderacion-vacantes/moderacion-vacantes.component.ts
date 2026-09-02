import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Vacante } from '../../../core/models/vacante.models';
import { VacanteService } from '../../../core/services/vacante.service';

/**
 * Panel de moderación institucional de ofertas laborales (HU-12).
 * Permite al administrador/moderador aprobar o rechazar (con motivo)
 * las vacantes que las empresas envían a revisión antes de publicarse.
 */
@Component({
  selector: 'app-moderacion-vacantes',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './moderacion-vacantes.component.html',
  styleUrl: './moderacion-vacantes.component.scss',
})
export class ModeracionVacantesComponent implements OnInit {
  private readonly vacanteService = inject(VacanteService);

  vacantes: Vacante[] = [];
  isLoading = false;
  errorMessage: string | null = null;
  toastMessage: string | null = null;
  toastEsError = false;

  page = 1;
  pageSize = 10;
  total = 0;
  totalPages = 1;

  // Modal de rechazo (pide motivo obligatorio)
  showRechazoModal = false;
  vacanteParaRechazar: Vacante | null = null;
  motivoRechazo = '';
  isProcessingAction = false;

  ngOnInit(): void {
    this.cargarPendientes();
  }

  cargarPendientes(): void {
    this.isLoading = true;
    this.errorMessage = null;

    this.vacanteService.listarPendientesRevision(this.page, this.pageSize).subscribe({
      next: (data) => {
        this.vacantes = data.items;
        this.total = data.total;
        this.totalPages = data.total_pages;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
        this.errorMessage = 'No se pudieron cargar las vacantes pendientes de revisión.';
      },
    });
  }

  irAPagina(nueva: number): void {
    if (nueva < 1 || nueva > this.totalPages || nueva === this.page) return;
    this.page = nueva;
    this.cargarPendientes();
  }

  aprobar(vacante: Vacante): void {
    this.isProcessingAction = true;
    this.vacanteService.moderarVacante(vacante.id, { aprobado: true }).subscribe({
      next: () => {
        this.isProcessingAction = false;
        this._quitarDeLista(vacante.id);
        this.showToast(`Vacante "${vacante.title}" aprobada y publicada.`);
      },
      error: () => {
        this.isProcessingAction = false;
        this.showToast('Error al aprobar la vacante.', true);
      },
    });
  }

  abrirModalRechazo(vacante: Vacante): void {
    this.vacanteParaRechazar = vacante;
    this.motivoRechazo = '';
    this.showRechazoModal = true;
  }

  cerrarModalRechazo(): void {
    this.showRechazoModal = false;
    this.vacanteParaRechazar = null;
    this.motivoRechazo = '';
  }

  confirmarRechazo(): void {
    if (!this.vacanteParaRechazar) return;
    if (!this.motivoRechazo.trim()) {
      this.showToast('Debés indicar el motivo del rechazo.', true);
      return;
    }

    this.isProcessingAction = true;
    const vacante = this.vacanteParaRechazar;

    this.vacanteService
      .moderarVacante(vacante.id, { aprobado: false, motivo_rechazo: this.motivoRechazo.trim() })
      .subscribe({
        next: () => {
          this.isProcessingAction = false;
          this.cerrarModalRechazo();
          this._quitarDeLista(vacante.id);
          this.showToast(`Vacante "${vacante.title}" rechazada. Se notificó a la empresa.`);
        },
        error: () => {
          this.isProcessingAction = false;
          this.showToast('Error al rechazar la vacante.', true);
        },
      });
  }

  private _quitarDeLista(id: string): void {
    this.vacantes = this.vacantes.filter((v) => v.id !== id);
    this.total = Math.max(0, this.total - 1);
  }

  private showToast(msg: string, esError = false): void {
    this.toastMessage = msg;
    this.toastEsError = esError;
    setTimeout(() => {
      if (this.toastMessage === msg) {
        this.toastMessage = null;
      }
    }, 4000);
  }
}
