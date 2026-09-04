import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  CandidatoTablero,
  EtapaItemRequest,
  EtapaSeleccion,
  HistorialEtapaItem,
  NotaInterna,
  TableroSeleccion,
} from '../../../core/models/seleccion.models';
import { VacanteResumen } from '../../../core/models/vacante.models';
import { SeleccionService } from '../../../core/services/seleccion.service';
import { VacanteService } from '../../../core/services/vacante.service';
import { AuthService } from '../../auth/auth.service';

@Component({
  selector: 'app-tablero-seleccion',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './tablero-seleccion.component.html',
  styleUrl: './tablero-seleccion.component.scss',
})
export class TableroSeleccionComponent implements OnInit {
  private readonly seleccionService = inject(SeleccionService);
  private readonly vacanteService = inject(VacanteService);
  readonly auth = inject(AuthService);

  // Vacantes disponibles para selección
  vacantes: VacanteResumen[] = [];
  vacanteSeleccionadaId = '';

  // Estado del Tablero Kanban
  tablero: TableroSeleccion | null = null;
  isLoading = false;
  errorMessage: string | null = null;

  // Modal: Mover Candidato
  showModalMover = false;
  candidatoAMover: CandidatoTablero | null = null;
  etapaDestinoId = '';
  observacionMovimiento = '';
  isSubmittingMover = false;

  // Modal: Descartar Candidato
  showModalDescartar = false;
  candidatoADescartar: CandidatoTablero | null = null;
  motivoDescarte = '';
  isSubmittingDescartar = false;

  // Modal: Configurar Etapas
  showModalConfigEtapas = false;
  etapasEditables: EtapaItemRequest[] = [];
  isSubmittingEtapas = false;

  // Modal: Ficha del Candidato (Notas & Historial)
  showModalFicha = false;
  candidatoFicha: CandidatoTablero | null = null;
  tabActivaFicha: 'info' | 'historial' | 'notas' = 'info';
  historialCandidato: HistorialEtapaItem[] = [];
  notasCandidato: NotaInterna[] = [];
  nuevaNotaTexto = '';
  isLoadingFicha = false;
  isSubmittingNota = false;

  // Toast
  toastMessage: string | null = null;

  ngOnInit(): void {
    this.cargarListaVacantes();
  }

  cargarListaVacantes(): void {
    this.vacanteService.buscarVacantes({ limit: 50 }).subscribe({
      next: (resp) => {
        this.vacantes = resp.items;
        if (this.vacantes.length > 0) {
          this.vacanteSeleccionadaId = this.vacantes[0].id;
          this.cargarTablero(this.vacanteSeleccionadaId);
        }
      },
      error: () => {
        this.errorMessage = 'No se pudieron cargar las ofertas de empleo.';
      },
    });
  }

  onCambiarVacante(): void {
    if (this.vacanteSeleccionadaId) {
      this.cargarTablero(this.vacanteSeleccionadaId);
    }
  }

  cargarTablero(vacanteId: string): void {
    this.isLoading = true;
    this.errorMessage = null;

    this.seleccionService.obtenerTablero(vacanteId).subscribe({
      next: (data) => {
        this.tablero = data;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
        this.errorMessage = 'Error al cargar el tablero de selección de esta vacante.';
      },
    });
  }

  // --- MOVIMIENTO DE CANDIDATO ---
  abrirModalMover(candidato: CandidatoTablero): void {
    this.candidatoAMover = candidato;
    this.observacionMovimiento = '';
    // Preseleccionar la siguiente etapa lógica si existe
    if (this.tablero && this.tablero.columnas.length > 0) {
      const idx = this.tablero.columnas.findIndex(
        (c) => c.stage.id === candidato.current_stage_id
      );
      if (idx >= 0 && idx + 1 < this.tablero.columnas.length) {
        this.etapaDestinoId = this.tablero.columnas[idx + 1].stage.id;
      } else {
        this.etapaDestinoId = this.tablero.columnas[0].stage.id;
      }
    }
    this.showModalMover = true;
  }

  confirmarMoverCandidato(): void {
    if (!this.candidatoAMover || !this.etapaDestinoId) return;

    this.isSubmittingMover = true;
    this.seleccionService
      .moverCandidato(this.candidatoAMover.application_id, {
        nueva_etapa_id: this.etapaDestinoId,
        observacion: this.observacionMovimiento || undefined,
      })
      .subscribe({
        next: () => {
          this.isSubmittingMover = false;
          this.showModalMover = false;
          this.mostrarToast('¡Candidato avanzado de etapa con éxito! Se envió la notificación.');
          this.cargarTablero(this.vacanteSeleccionadaId);
        },
        error: (err) => {
          this.isSubmittingMover = false;
          const msg = err.error?.detail || 'No se pudo mover el candidato.';
          this.mostrarToast(msg, true);
        },
      });
  }

  // --- DESCARTE DE CANDIDATO ---
  abrirModalDescartar(candidato: CandidatoTablero): void {
    this.candidatoADescartar = candidato;
    this.motivoDescarte = '';
    this.showModalDescartar = true;
  }

  confirmarDescartarCandidato(): void {
    if (!this.candidatoADescartar) return;

    this.isSubmittingDescartar = true;
    this.seleccionService
      .descartarCandidato(this.candidatoADescartar.application_id, {
        motivo: this.motivoDescarte || undefined,
      })
      .subscribe({
        next: () => {
          this.isSubmittingDescartar = false;
          this.showModalDescartar = false;
          this.mostrarToast('Candidato descartado del proceso.');
          this.cargarTablero(this.vacanteSeleccionadaId);
        },
        error: (err) => {
          this.isSubmittingDescartar = false;
          const msg = err.error?.detail || 'No se pudo descartar el candidato.';
          this.mostrarToast(msg, true);
        },
      });
  }

  // --- CONFIGURAR ETAPAS ---
  abrirModalConfigEtapas(): void {
    if (!this.tablero) return;
    this.etapasEditables = this.tablero.columnas.map((c) => ({
      id: c.stage.id,
      stage_number: c.stage.stage_number,
      name: c.stage.name,
      description: c.stage.description,
      is_terminal: c.stage.is_terminal,
    }));
    this.showModalConfigEtapas = true;
  }

  agregarNuevaEtapa(): void {
    const nextNum = this.etapasEditables.length + 1;
    this.etapasEditables.push({
      stage_number: nextNum,
      name: `Etapa ${nextNum}`,
      description: '',
      is_terminal: false,
    });
  }

  eliminarEtapa(index: number): void {
    if (this.etapasEditables.length <= 1) {
      this.mostrarToast('Debe existir al menos una etapa en el proceso.', true);
      return;
    }
    this.etapasEditables.splice(index, 1);
    this.etapasEditables.forEach((e, idx) => (e.stage_number = idx + 1));
  }

  guardarConfiguracionEtapas(): void {
    this.isSubmittingEtapas = true;
    this.seleccionService
      .configurarEtapas(this.vacanteSeleccionadaId, { etapas: this.etapasEditables })
      .subscribe({
        next: () => {
          this.isSubmittingEtapas = false;
          this.showModalConfigEtapas = false;
          this.mostrarToast('Etapas del proceso actualizadas exitosamente.');
          this.cargarTablero(this.vacanteSeleccionadaId);
        },
        error: (err) => {
          this.isSubmittingEtapas = false;
          const msg = err.error?.detail || 'Error al guardar las etapas.';
          this.mostrarToast(msg, true);
        },
      });
  }

  // --- FICHA DEL CANDIDATO (HISTORIAL Y NOTAS) ---
  abrirFichaCandidato(candidato: CandidatoTablero, tab: 'info' | 'historial' | 'notas' = 'info'): void {
    this.candidatoFicha = candidato;
    this.tabActivaFicha = tab;
    this.nuevaNotaTexto = '';
    this.showModalFicha = true;
    this.cargarDatosFicha(candidato.application_id);
  }

  cargarDatosFicha(applicationId: string): void {
    this.isLoadingFicha = true;
    this.seleccionService.obtenerHistorial(applicationId).subscribe({
      next: (h) => {
        this.historialCandidato = h.historial;
      },
    });

    this.seleccionService.obtenerNotas(applicationId).subscribe({
      next: (n) => {
        this.notasCandidato = n;
        this.isLoadingFicha = false;
      },
      error: () => {
        this.isLoadingFicha = false;
      },
    });
  }

  guardarNotaInterna(): void {
    if (!this.candidatoFicha || !this.nuevaNotaTexto.trim()) return;

    this.isSubmittingNota = true;
    this.seleccionService
      .registrarNota(this.candidatoFicha.application_id, {
        content: this.nuevaNotaTexto.trim(),
      })
      .subscribe({
        next: (nota) => {
          this.isSubmittingNota = false;
          this.nuevaNotaTexto = '';
          this.notasCandidato.unshift(nota);
          if (this.candidatoFicha) {
            this.candidatoFicha.notas_count++;
          }
          this.mostrarToast('Nota interna registrada.');
        },
        error: () => {
          this.isSubmittingNota = false;
          this.mostrarToast('No se pudo guardar la nota interna.', true);
        },
      });
  }

  mostrarToast(mensaje: string, isError = false): void {
    this.toastMessage = mensaje;
    setTimeout(() => {
      if (this.toastMessage === mensaje) {
        this.toastMessage = null;
      }
    }, 4000);
  }
}

