import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CarreraOpcion, TableroIndicadores } from './indicadores.models';
import { IndicadoresService } from './indicadores.service';

@Component({
  selector: 'app-indicadores',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './indicadores.component.html',
  styleUrls: ['./indicadores.component.scss'],
})
export class IndicadoresComponent implements OnInit {
  private readonly indicadoresService = inject(IndicadoresService);

  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  // Filtros
  readonly carreras = signal<CarreraOpcion[]>([]);
  readonly periodos = signal<string[]>([]);
  readonly carreraSeleccionada = signal<string>('');
  readonly periodoSeleccionado = signal<string>('');

  // Datos del tablero
  readonly tablero = signal<TableroIndicadores | null>(null);

  ngOnInit(): void {
    this.cargarFiltrosYDatos();
  }

  cargarFiltrosYDatos(): void {
    this.cargando.set(true);
    this.error.set(null);

    this.indicadoresService.obtenerFiltros().subscribe({
      next: (filtros) => {
        this.carreras.set(filtros.carreras || []);
        this.periodos.set(filtros.periodos || []);
        this.cargarTablero();
      },
      error: () => {
        this.cargando.set(false);
        this.error.set('No se pudieron cargar los filtros del tablero de indicadores.');
      },
    });
  }

  cargarTablero(): void {
    this.cargando.set(true);
    this.error.set(null);

    const carreraId = this.carreraSeleccionada() || null;
    const periodo = this.periodoSeleccionado() || null;

    this.indicadoresService.consultarTablero(carreraId, periodo).subscribe({
      next: (data) => {
        this.tablero.set(data);
        this.cargando.set(false);
      },
      error: () => {
        this.cargando.set(false);
        this.error.set('Error al calcular los indicadores de inserción laboral.');
      },
    });
  }

  onCarreraChange(carreraId: string): void {
    this.carreraSeleccionada.set(carreraId);
    this.cargarTablero();
  }

  onPeriodoChange(periodo: string): void {
    this.periodoSeleccionado.set(periodo);
    this.cargarTablero();
  }

  limpiarFiltros(): void {
    this.carreraSeleccionada.set('');
    this.periodoSeleccionado.set('');
    this.cargarTablero();
  }
}
