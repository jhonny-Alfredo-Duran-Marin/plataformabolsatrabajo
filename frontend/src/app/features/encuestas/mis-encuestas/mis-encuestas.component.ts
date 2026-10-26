import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { mensajeDeError } from '../../moderacion/denuncias.models';
import { MiEncuesta } from '../encuestas.models';
import { EncuestasService } from '../encuestas.service';

/** HU-30: las encuestas de situación laboral que la universidad le envió al egresado. */
@Component({
  selector: 'app-mis-encuestas',
  standalone: true,
  imports: [DatePipe, RouterLink],
  templateUrl: './mis-encuestas.component.html',
  styleUrl: './mis-encuestas.component.scss',
})
export class MisEncuestasComponent implements OnInit {
  private readonly servicio = inject(EncuestasService);

  readonly encuestas = signal<MiEncuesta[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  readonly pendientes = computed(() => this.encuestas().filter((e) => !e.respondida));
  readonly respondidas = computed(() => this.encuestas().filter((e) => e.respondida));

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.servicio.mias().subscribe({
      next: (encuestas) => {
        this.encuestas.set(encuestas);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err, 'No se pudieron cargar tus encuestas.'));
        this.cargando.set(false);
      },
    });
  }
}
