import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../auth/auth.service';
import { BitacoraLog, BitacoraFiltros } from './bitacora.model';
import { BitacoraService } from './bitacora.service';

const TAMANIO_PAGINA = 15;

@Component({
  selector: 'app-bitacora',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './bitacora.component.html',
  styleUrl: './bitacora.component.scss',
})
export class BitacoraComponent implements OnInit {
  readonly logs = signal<BitacoraLog[]>([]);
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly paginaActual = signal(1);

  readonly totalPaginas = computed(() => Math.max(1, Math.ceil(this.logs().length / TAMANIO_PAGINA)));

  readonly logsPagina = computed(() => {
    const inicio = (this.paginaActual() - 1) * TAMANIO_PAGINA;
    return this.logs().slice(inicio, inicio + TAMANIO_PAGINA);
  });

  filtros: BitacoraFiltros = {
    usuarioId: null,
    modulo: '',
    accion: '',
    fechaDesde: '',
    fechaHasta: '',
  };

  constructor(
    private readonly bitacoraService: BitacoraService,
    private readonly auth: AuthService,
  ) {}

  ngOnInit(): void {
    this.buscar();
  }

  buscar(): void {
    const token = this.auth.token();
    if (!token) {
      this.error.set('Inicia sesión como administrador para consultar la bitácora.');
      return;
    }

    this.cargando.set(true);
    this.error.set(null);
    this.bitacoraService.listar(token, this.filtros).subscribe({
      next: (logs) => {
        this.logs.set(logs);
        this.paginaActual.set(1);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar la bitácora. Verifica los filtros.');
        this.cargando.set(false);
      },
    });
  }

  irAPagina(pagina: number): void {
    if (pagina < 1 || pagina > this.totalPaginas()) return;
    this.paginaActual.set(pagina);
  }

  exportar(formato: 'excel' | 'pdf'): void {
    const token = this.auth.token();
    if (!token) {
      this.error.set('Inicia sesión como administrador para exportar la bitácora.');
      return;
    }

    this.bitacoraService.exportar(token, formato, this.filtros).subscribe({
      next: (blob) => this.descargar(blob, formato === 'excel' ? 'bitacora.xlsx' : 'bitacora.pdf'),
      error: () => this.error.set('No se pudo exportar la bitácora.'),
    });
  }

  private descargar(blob: Blob, nombreArchivo: string): void {
    const url = window.URL.createObjectURL(blob);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = nombreArchivo;
    enlace.click();
    window.URL.revokeObjectURL(url);
  }
}
