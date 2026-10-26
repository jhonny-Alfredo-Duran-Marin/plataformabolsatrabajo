import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { mensajeDeError } from '../../moderacion/denuncias.models';
import {
  FormularioEncuesta,
  PreguntaEncuesta,
  ValoresEncuesta,
  armarRespuestas,
  esObligatoria,
  faltanRespuestas,
  preguntasVisibles,
} from '../encuestas.models';
import { EncuestasService } from '../encuestas.service';

/** HU-30: el egresado responde la encuesta de situación laboral de un período. */
@Component({
  selector: 'app-responder-encuesta',
  standalone: true,
  imports: [DatePipe, FormsModule, RouterLink],
  templateUrl: './responder-encuesta.component.html',
  styleUrl: './responder-encuesta.component.scss',
})
export class ResponderEncuestaComponent implements OnInit {
  private readonly servicio = inject(EncuestasService);
  private readonly ruta = inject(ActivatedRoute);

  /** Las cinco opciones de la escala de relación con la carrera. */
  readonly escala = [1, 2, 3, 4, 5];

  readonly formulario = signal<FormularioEncuesta | null>(null);
  readonly cargando = signal(true);
  /** Por qué no se puede responder (ya respondió, cerró, no le corresponde...). */
  readonly bloqueo = signal<string | null>(null);
  readonly enviando = signal(false);
  readonly errorEnvio = signal<string | null>(null);
  readonly enviada = signal<string | null>(null);

  private readonly opciones = signal<Record<string, string>>({});
  private readonly textos = signal<Record<string, string>>({});
  private readonly numeros = signal<Record<string, number | null>>({});

  private readonly valores = computed<ValoresEncuesta>(() => ({
    opciones: this.opciones(),
    textos: this.textos(),
    numeros: this.numeros(),
  }));
  readonly preguntas = computed(() => {
    const f = this.formulario();
    return f ? preguntasVisibles(f.preguntas, this.valores()) : [];
  });
  readonly puedeEnviar = computed(() => {
    const f = this.formulario();
    return !!f && !this.enviando() && !faltanRespuestas(f.preguntas, this.valores());
  });

  ngOnInit(): void {
    const id = this.ruta.snapshot.paramMap.get('id') ?? '';
    this.servicio.formulario(id).subscribe({
      next: (f) => {
        this.formulario.set(f);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.bloqueo.set(mensajeDeError(err, 'No se pudo cargar la encuesta.'));
        this.cargando.set(false);
      },
    });
  }

  obligatoria(pregunta: PreguntaEncuesta): boolean {
    const f = this.formulario();
    return !!f && esObligatoria(pregunta, this.valores(), f.preguntas);
  }

  opcionElegida(pregunta: PreguntaEncuesta): string {
    return this.opciones()[pregunta.id] ?? '';
  }

  elegirOpcion(pregunta: PreguntaEncuesta, opcionId: string): void {
    this.opciones.update((o) => ({ ...o, [pregunta.id]: opcionId }));
  }

  texto(pregunta: PreguntaEncuesta): string {
    return this.textos()[pregunta.id] ?? '';
  }

  escribir(pregunta: PreguntaEncuesta, valor: string): void {
    this.textos.update((t) => ({ ...t, [pregunta.id]: valor }));
  }

  numero(pregunta: PreguntaEncuesta): number | null {
    return this.numeros()[pregunta.id] ?? null;
  }

  poner(pregunta: PreguntaEncuesta, valor: number | string | null): void {
    // Un campo numérico vacío llega como '' o null: se toma como sin responder.
    const numero = valor === '' || valor == null ? null : Number(valor);
    this.numeros.update((n) => ({ ...n, [pregunta.id]: Number.isFinite(numero) ? numero : null }));
  }

  enviar(): void {
    const f = this.formulario();
    if (!f || !this.puedeEnviar()) return;
    this.enviando.set(true);
    this.errorEnvio.set(null);
    this.servicio.responder(f.id, armarRespuestas(f.preguntas, this.valores())).subscribe({
      next: (r) => {
        this.enviando.set(false);
        this.enviada.set(r.mensaje);
      },
      error: (err: HttpErrorResponse) => {
        this.enviando.set(false);
        const mensaje = mensajeDeError(err, 'No se pudo enviar tu respuesta. Probá de nuevo.');
        // Una encuesta ya respondida o cerrada no se arregla reintentando.
        if (err.status === 409 || err.status === 404 || /cerrada/i.test(mensaje)) this.bloqueo.set(mensaje);
        else this.errorEnvio.set(mensaje);
      },
    });
  }
}
