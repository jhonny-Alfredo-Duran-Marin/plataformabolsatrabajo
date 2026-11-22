import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../auth/auth.service';
import { mensajeDeError } from '../../moderacion/denuncias.models';
import {
  BrechaHabilidades,
  CarreraOpcion,
  etiquetaPeriodo,
} from './analisis-predictivo.models';
import { AnalisisPredictivoService } from './analisis-predictivo.service';

/** HU-33: habilidades que piden las vacantes de una carrera frente a las que declaran sus egresados. */
@Component({
  selector: 'app-analisis-predictivo',
  standalone: true,
  imports: [DatePipe, FormsModule],
  templateUrl: './analisis-predictivo.component.html',
  styleUrl: './analisis-predictivo.component.scss',
})
export class AnalisisPredictivoComponent implements OnInit {
  private readonly servicio = inject(AnalisisPredictivoService);
  readonly auth = inject(AuthService);

  readonly etiquetaPeriodo = etiquetaPeriodo;

  // Selectores
  readonly carreras = signal<CarreraOpcion[]>([]);
  readonly periodos = signal<string[]>([]);
  readonly cargandoFiltros = signal(true);
  readonly errorFiltros = signal<string | null>(null);
  readonly carreraId = signal('');
  readonly periodo = signal('');

  // Resultado
  readonly resultado = signal<BrechaHabilidades | null>(null);
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);

  readonly puedeGenerar = computed(() => this.carreraId() !== '' && !this.cargando());
  /** Cuántas habilidades tienen brecha positiva: las que conviene reforzar. */
  readonly conBrecha = computed(() => (this.resultado()?.habilidades ?? []).filter((h) => h.brecha > 0).length);

  ngOnInit(): void {
    this.cargarFiltros();
  }

  cargarFiltros(): void {
    this.cargandoFiltros.set(true);
    this.errorFiltros.set(null);
    this.servicio.filtros().subscribe({
      next: (f) => {
        this.carreras.set(f.carreras);
        this.periodos.set(f.periodos);
        this.cargandoFiltros.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.cargandoFiltros.set(false);
        this.errorFiltros.set(mensajeDeError(err, 'No se pudieron cargar las carreras y los períodos.'));
      },
    });
  }

  /** Al cambiar un filtro, el resultado anterior ya no corresponde a lo elegido. */
  alCambiarFiltro(): void {
    this.resultado.set(null);
    this.error.set(null);
  }

  limpiar(): void {
    this.carreraId.set('');
    this.periodo.set('');
    this.alCambiarFiltro();
  }

  generar(): void {
    if (!this.puedeGenerar()) return;
    this.cargando.set(true);
    this.error.set(null);
    this.resultado.set(null);
    this.servicio.brechaHabilidades(this.carreraId(), this.periodo() || null).subscribe({
      next: (r) => {
        this.resultado.set(r);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.cargando.set(false);
        this.error.set(mensajeDeError(err, 'No se pudo calcular la brecha de habilidades.'));
      },
    });
  }
}
