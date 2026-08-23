import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AdminTokenService } from '../../../core/services/admin-token.service';
import { BitacoraLog, BitacoraFiltros } from './bitacora.model';
import { BitacoraService } from './bitacora.service';

@Component({
  selector: 'app-bitacora',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './bitacora.component.html',
  styleUrl: './bitacora.component.scss',
})
export class BitacoraComponent {
  readonly logs = signal<BitacoraLog[]>([]);
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);

  filtros: BitacoraFiltros = {
    usuarioId: null,
    modulo: '',
    accion: '',
    fechaDesde: '',
    fechaHasta: '',
  };

  constructor(
    private readonly bitacoraService: BitacoraService,
    readonly adminToken: AdminTokenService,
  ) {}

  guardarToken(token: string): void {
    this.adminToken.guardar(token);
  }

  buscar(): void {
    const token = this.adminToken.token();
    if (!token) {
      this.error.set('Pega un token de administrador para consultar la bitácora.');
      return;
    }

    this.cargando.set(true);
    this.error.set(null);
    this.bitacoraService.listar(token, this.filtros).subscribe({
      next: (logs) => {
        this.logs.set(logs);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar la bitácora. Verifica el token y los filtros.');
        this.cargando.set(false);
      },
    });
  }

  exportar(formato: 'excel' | 'pdf'): void {
    const token = this.adminToken.token();
    if (!token) {
      this.error.set('Pega un token de administrador para exportar la bitácora.');
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
