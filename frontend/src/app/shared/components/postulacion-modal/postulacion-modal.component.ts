import { Component, Input, Output, EventEmitter, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PostulacionService, ScreeningQuestion, ApplicationAnswerCreate } from '../../../core/services/postulacion.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-postulacion-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './postulacion-modal.component.html',
  styleUrls: ['./postulacion-modal.component.scss']
})
export class PostulacionModalComponent implements OnInit {
  @Input() jobId!: string;
  @Input() perfilPorcentaje: number = 100;
  @Output() onClose = new EventEmitter<void>();
  @Output() onPostulacionExitosa = new EventEmitter<void>();

  private postulacionService = inject(PostulacionService);
  private toastService = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);

  preguntas: ScreeningQuestion[] = [];
  respuestas: { [key: string]: ApplicationAnswerCreate } = {};
  isLoading = false;
  isSubmitting = false;
  mostrarAdvertencia = false;
  
  ngOnInit() {
    this.mostrarAdvertencia = this.perfilPorcentaje < 60;
    this.cargarPreguntas();
  }

  cargarPreguntas() {
    this.isLoading = true;
    this.postulacionService.getPreguntasFiltro(this.jobId).subscribe({
      next: (data) => {
        this.preguntas = data || [];
        this.isLoading = false;
        // Inicializar respuestas
        this.preguntas.forEach(q => {
          this.respuestas[q.id] = { question_id: q.id };
        });
        this.cdr.detectChanges();
      },
      error: (err: any) => {
        this.toastService.error('Error al cargar las preguntas de filtro');
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  confirmarPostulacion() {
    // Validar requeridos
    for (let q of this.preguntas) {
      if (q.is_required) {
        let resp = this.respuestas[q.id];
        if (!resp.answer_text && !resp.selected_option_id && (resp.answer_number === undefined || resp.answer_number === null)) {
          this.toastService.warning('Por favor, responde a todas las preguntas requeridas.');
          return;
        }
      }
    }

    this.isSubmitting = true;
    const answersArray = Object.values(this.respuestas).filter(r => r.answer_text || r.selected_option_id || r.answer_number != null);

    this.postulacionService.postularse({ job_id: this.jobId, answers: answersArray }).subscribe({
      next: (res) => {
        this.toastService.success('¡Postulación exitosa!');
        this.isSubmitting = false;
        this.cdr.detectChanges();
        this.onPostulacionExitosa.emit();
        this.cerrar();
      },
      error: (err: any) => {
        const msg = err.error?.detail || 'Error al enviar la postulación.';
        this.toastService.error(msg);
        this.isSubmitting = false;
        this.cdr.detectChanges();
      }
    });
  }

  cerrar() {
    this.onClose.emit();
  }
}
