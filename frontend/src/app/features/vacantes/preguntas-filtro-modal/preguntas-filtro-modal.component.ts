import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { PreguntaFiltro, PreguntaFiltroOpcion } from '../../../core/models/vacante.models';
import { ToastService } from '../../../core/services/toast.service';
import { VacanteService } from '../../../core/services/vacante.service';

/** Formulario de una pregunta nueva en edición dentro del modal. */
interface PreguntaEnEdicion {
  question_text: string;
  question_type: 'text' | 'number' | 'single_choice';
  is_required: boolean;
  is_knockout: boolean;
  options: PreguntaFiltroOpcion[];
}

function preguntaVacia(): PreguntaEnEdicion {
  return {
    question_text: '',
    question_type: 'text',
    is_required: true,
    is_knockout: false,
    options: [],
  };
}

@Component({
  selector: 'app-preguntas-filtro-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './preguntas-filtro-modal.component.html',
  styleUrl: './preguntas-filtro-modal.component.scss',
})
export class PreguntasFiltroModalComponent implements OnInit {
  @Input({ required: true }) vacanteId!: string;
  @Input() vacanteTitulo = '';
  @Output() cerrar = new EventEmitter<void>();

  private readonly vacanteService = inject(VacanteService);
  private readonly toast = inject(ToastService);
  private readonly cdr = inject(ChangeDetectorRef);

  preguntas: PreguntaFiltro[] = [];
  cargando = false;
  guardando = false;

  nuevaPregunta: PreguntaEnEdicion = preguntaVacia();
  mostrandoFormulario = false;

  ngOnInit(): void {
    this.cargarPreguntas();
  }

  cargarPreguntas(): void {
    this.cargando = true;
    this.vacanteService.listarPreguntasFiltro(this.vacanteId).subscribe({
      next: (data) => {
        this.preguntas = data ?? [];
        this.cargando = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.cargando = false;
        this.cdr.markForCheck();
      },
    });
  }

  abrirFormularioNuevaPregunta(): void {
    this.nuevaPregunta = preguntaVacia();
    this.mostrandoFormulario = true;
  }

  cancelarFormulario(): void {
    this.mostrandoFormulario = false;
  }

  agregarOpcion(): void {
    this.nuevaPregunta.options.push({ option_text: '', is_accepted: true, position: this.nuevaPregunta.options.length });
  }

  quitarOpcion(index: number): void {
    this.nuevaPregunta.options.splice(index, 1);
  }

  onTipoChange(): void {
    if (this.nuevaPregunta.question_type !== 'single_choice') {
      this.nuevaPregunta.options = [];
      this.nuevaPregunta.is_knockout = false;
    } else if (this.nuevaPregunta.options.length === 0) {
      this.agregarOpcion();
      this.agregarOpcion();
    }
  }

  guardarNuevaPregunta(): void {
    if (!this.nuevaPregunta.question_text.trim()) {
      this.toast.warning('La pregunta necesita un texto.');
      return;
    }
    if (this.nuevaPregunta.question_type === 'single_choice' && this.nuevaPregunta.options.length < 2) {
      this.toast.warning('Una pregunta de selección necesita al menos dos opciones.');
      return;
    }

    this.guardando = true;
    this.vacanteService
      .crearPreguntaFiltro(this.vacanteId, {
        question_text: this.nuevaPregunta.question_text.trim(),
        question_type: this.nuevaPregunta.question_type,
        is_required: this.nuevaPregunta.is_required,
        is_knockout: this.nuevaPregunta.is_knockout,
        position: this.preguntas.length,
        options: this.nuevaPregunta.options,
      })
      .subscribe({
        next: () => {
          this.toast.success('Pregunta de filtro agregada.');
          this.guardando = false;
          this.mostrandoFormulario = false;
          this.cargarPreguntas();
        },
        error: () => {
          this.guardando = false;
          this.cdr.markForCheck();
        },
      });
  }

  eliminarPregunta(pregunta: PreguntaFiltro): void {
    if (!confirm('¿Eliminar esta pregunta de filtro?')) return;

    this.vacanteService.eliminarPreguntaFiltro(this.vacanteId, pregunta.id).subscribe({
      next: () => {
        this.toast.success('Pregunta eliminada.');
        this.cargarPreguntas();
      },
      error: () => this.cdr.markForCheck(),
    });
  }

  cerrarModal(): void {
    this.cerrar.emit();
  }
}
