import {
  Component,
  OnInit,
  signal,
  computed,
  inject,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { SeleccionService } from '../seleccion.service';
import {
  CandidatoPipelineItem,
  EtapaItem,
  EtapaResponse,
  NotaInternaResponse,
  PipelineVacanteResponse,
  VacanteResumenSeleccion,
} from '../seleccion.models';

@Component({
  selector: 'app-pipeline-seleccion',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './pipeline-seleccion.component.html',
  styleUrls: ['./pipeline-seleccion.component.scss'],
  changeDetection: ChangeDetectionStrategy.Default,
})
export class PipelineSeleccionComponent implements OnInit {
  private readonly svc = inject(SeleccionService);

  // ── Estado general ──────────────────────────────────────────────────
  vacantes = signal<VacanteResumenSeleccion[]>([]);
  vacanteSeleccionadaId = signal<string | null>(null);
  pipeline = signal<PipelineVacanteResponse | null>(null);
  cargandoVacantes = signal(false);
  cargandoPipeline = signal(false);
  error = signal<string | null>(null);

  // ── Modal: Configurar Etapas ─────────────────────────────────────────
  mostrarModalEtapas = signal(false);
  etapasEditor = signal<EtapaItem[]>([]);
  guardandoEtapas = signal(false);
  errorEtapas = signal<string | null>(null);

  // ── Modal: Avanzar Etapa ─────────────────────────────────────────────
  mostrarModalAvanzar = signal(false);
  candidatoActivo = signal<CandidatoPipelineItem | null>(null);
  etapaDestinoId = signal<string>('');
  observacionAvance = signal<string>('');
  procesandoAvance = signal(false);
  errorAvance = signal<string | null>(null);

  // ── Modal: Descartar Candidato ───────────────────────────────────────
  mostrarModalDescartar = signal(false);
  motivoDescarte = signal<string>('');
  procesandoDescarte = signal(false);
  errorDescarte = signal<string | null>(null);

  // ── Modal: Notas Internas ────────────────────────────────────────────
  mostrarModalNotas = signal(false);
  notas = signal<NotaInternaResponse[]>([]);
  nuevaNota = signal<string>('');
  cargandoNotas = signal(false);
  guardandoNota = signal(false);
  errorNotas = signal<string | null>(null);

  // ── Computed ─────────────────────────────────────────────────────────
  vacanteActual = computed(() => this.pipeline()?.vacante ?? null);
  etapas = computed(() => this.pipeline()?.etapas ?? []);
  candidatos = computed(() => this.pipeline()?.candidatos ?? []);

  candidatosPorEtapa = computed(() => {
    const mapa: Record<string, CandidatoPipelineItem[]> = {};
    for (const etapa of this.etapas()) {
      mapa[etapa.id] = this.candidatos().filter(
        (c) => c.etapa_actual_id === etapa.id && c.estado !== 'rejected' && c.estado !== 'withdrawn'
      );
    }
    mapa['__sin_etapa__'] = this.candidatos().filter(
      (c) => !c.etapa_actual_id && c.estado !== 'rejected' && c.estado !== 'withdrawn'
    );
    mapa['__descartados__'] = this.candidatos().filter(
      (c) => c.estado === 'rejected' || c.estado === 'withdrawn'
    );
    return mapa;
  });

  etapasParaAvanzar = computed(() => {
    const candidato = this.candidatoActivo();
    if (!candidato) return this.etapas();
    return this.etapas().filter((e) => e.id !== candidato.etapa_actual_id);
  });

  ngOnInit(): void {
    this.cargarVacantes();
  }

  cargarVacantes(): void {
    this.cargandoVacantes.set(true);
    this.error.set(null);
    this.svc.listarVacantes().subscribe({
      next: (data) => {
        this.vacantes.set(data);
        if (data.length > 0 && !this.vacanteSeleccionadaId()) {
          const preferida = data.find((v) => v.total_postulantes > 0) ?? data[0];
          this.seleccionarVacante(preferida.id);
        }
        this.cargandoVacantes.set(false);

      },
      error: (e: HttpErrorResponse) => {
        this.error.set(e.error?.detail ?? 'Error al cargar las vacantes.');
        this.cargandoVacantes.set(false);
      },
    });
  }

  seleccionarVacante(id: string): void {
    this.vacanteSeleccionadaId.set(id);
    this.cargarPipeline(id);
  }

  cargarPipeline(id: string): void {
    this.cargandoPipeline.set(true);
    this.svc.obtenerPipeline(id).subscribe({
      next: (data) => {
        this.pipeline.set(data);
        this.cargandoPipeline.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.error.set(e.error?.detail ?? 'Error al cargar el pipeline.');
        this.cargandoPipeline.set(false);
      },
    });
  }

  // ── Configurar Etapas ────────────────────────────────────────────────
  abrirModalEtapas(): void {
    const etapasActuales = this.etapas().map((e) => ({
      id: e.id,
      stage_number: e.stage_number,
      name: e.name,
      description: e.description ?? '',
      is_terminal: e.is_terminal,
    }));
    this.etapasEditor.set(etapasActuales.length > 0 ? etapasActuales : [this.nuevaEtapaVacia(1)]);
    this.errorEtapas.set(null);
    this.mostrarModalEtapas.set(true);
  }

  cerrarModalEtapas(): void {
    this.mostrarModalEtapas.set(false);
  }

  nuevaEtapaVacia(numero: number): EtapaItem {
    return { stage_number: numero, name: '', description: '', is_terminal: false };
  }

  agregarEtapa(): void {
    const lista = [...this.etapasEditor()];
    lista.push(this.nuevaEtapaVacia(lista.length + 1));
    this.etapasEditor.set(lista);
  }

  eliminarEtapa(idx: number): void {
    const lista = this.etapasEditor().filter((_, i) => i !== idx);
    lista.forEach((e, i) => (e.stage_number = i + 1));
    this.etapasEditor.set([...lista]);
  }

  moverEtapa(idx: number, dir: -1 | 1): void {
    const lista = [...this.etapasEditor()];
    const nuevoIdx = idx + dir;
    if (nuevoIdx < 0 || nuevoIdx >= lista.length) return;
    [lista[idx], lista[nuevoIdx]] = [lista[nuevoIdx], lista[idx]];
    lista.forEach((e, i) => (e.stage_number = i + 1));
    this.etapasEditor.set(lista);
  }

  guardarEtapas(): void {
    const id = this.vacanteSeleccionadaId();
    if (!id) return;
    const etapas = this.etapasEditor();
    if (etapas.some((e) => !e.name.trim())) {
      this.errorEtapas.set('Todas las etapas deben tener un nombre.');
      return;
    }
    this.guardandoEtapas.set(true);
    this.errorEtapas.set(null);
    this.svc.configurarEtapas(id, { etapas }).subscribe({
      next: () => {
        this.mostrarModalEtapas.set(false);
        this.cargarPipeline(id);
        this.guardandoEtapas.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.errorEtapas.set(e.error?.detail ?? 'Error al guardar las etapas.');
        this.guardandoEtapas.set(false);
      },
    });
  }

  // ── Avanzar Etapa ────────────────────────────────────────────────────
  abrirModalAvanzar(candidato: CandidatoPipelineItem): void {
    this.candidatoActivo.set(candidato);
    this.etapaDestinoId.set('');
    this.observacionAvance.set('');
    this.errorAvance.set(null);
    this.mostrarModalAvanzar.set(true);
  }

  cerrarModalAvanzar(): void {
    this.mostrarModalAvanzar.set(false);
  }

  confirmarAvance(): void {
    const candidato = this.candidatoActivo();
    if (!candidato || !this.etapaDestinoId()) {
      this.errorAvance.set('Seleccione la etapa de destino.');
      return;
    }
    this.procesandoAvance.set(true);
    this.errorAvance.set(null);
    this.svc
      .avanzarEtapa(candidato.postulacion_id, {
        stage_id: this.etapaDestinoId(),
        observacion: this.observacionAvance() || null,
      })
      .subscribe({
        next: () => {
          this.mostrarModalAvanzar.set(false);
          this.cargarPipeline(this.vacanteSeleccionadaId()!);
          this.procesandoAvance.set(false);
        },
        error: (e: HttpErrorResponse) => {
          this.errorAvance.set(e.error?.detail ?? 'Error al avanzar la etapa.');
          this.procesandoAvance.set(false);
        },
      });
  }

  // ── Descartar Candidato ──────────────────────────────────────────────
  abrirModalDescartar(candidato: CandidatoPipelineItem): void {
    this.candidatoActivo.set(candidato);
    this.motivoDescarte.set('');
    this.errorDescarte.set(null);
    this.mostrarModalDescartar.set(true);
  }

  cerrarModalDescartar(): void {
    this.mostrarModalDescartar.set(false);
  }

  confirmarDescarte(): void {
    const candidato = this.candidatoActivo();
    if (!candidato) return;
    this.procesandoDescarte.set(true);
    this.errorDescarte.set(null);
    this.svc
      .descartarCandidato(candidato.postulacion_id, { motivo: this.motivoDescarte() || null })
      .subscribe({
        next: () => {
          this.mostrarModalDescartar.set(false);
          this.cargarPipeline(this.vacanteSeleccionadaId()!);
          this.procesandoDescarte.set(false);
        },
        error: (e: HttpErrorResponse) => {
          this.errorDescarte.set(e.error?.detail ?? 'Error al descartar al candidato.');
          this.procesandoDescarte.set(false);
        },
      });
  }

  // ── Notas Internas ───────────────────────────────────────────────────
  abrirModalNotas(candidato: CandidatoPipelineItem): void {
    this.candidatoActivo.set(candidato);
    this.notas.set([]);
    this.nuevaNota.set('');
    this.errorNotas.set(null);
    this.mostrarModalNotas.set(true);
    this.cargarNotas(candidato.postulacion_id);
  }

  cerrarModalNotas(): void {
    this.mostrarModalNotas.set(false);
  }

  cargarNotas(idPostulacion: string): void {
    this.cargandoNotas.set(true);
    this.svc.listarNotas(idPostulacion).subscribe({
      next: (data) => {
        this.notas.set(data);
        this.cargandoNotas.set(false);
      },
      error: () => {
        this.cargandoNotas.set(false);
      },
    });
  }

  enviarNota(): void {
    const candidato = this.candidatoActivo();
    if (!candidato || !this.nuevaNota().trim()) return;
    this.guardandoNota.set(true);
    this.errorNotas.set(null);
    this.svc.agregarNota(candidato.postulacion_id, { content: this.nuevaNota().trim() }).subscribe({
      next: (nota) => {
        this.notas.update((prev) => [nota, ...prev]);
        this.nuevaNota.set('');
        this.guardandoNota.set(false);
      },
      error: (e: HttpErrorResponse) => {
        this.errorNotas.set(e.error?.detail ?? 'Error al guardar la nota.');
        this.guardandoNota.set(false);
      },
    });
  }

  // ── Helpers ──────────────────────────────────────────────────────────
  initials(nombre: string): string {
    return nombre
      .split(' ')
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase() ?? '')
      .join('');
  }

  trackById(_: number, item: { id: string }): string {
    return item.id;
  }

  trackByPostulacion(_: number, item: CandidatoPipelineItem): string {
    return item.postulacion_id;
  }

  trackByIdx(idx: number): number {
    return idx;
  }

  formatFecha(fecha: string): string {
    return new Date(fecha).toLocaleDateString('es-BO', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  formatHora(fecha: string): string {
    return new Date(fecha).toLocaleString('es-BO', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
