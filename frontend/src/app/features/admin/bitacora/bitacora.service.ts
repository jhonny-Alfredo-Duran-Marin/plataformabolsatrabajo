import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { BitacoraLog, BitacoraFiltros } from './bitacora.model';
import { environment } from '../../../../environments/environment';

const API_BASE = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class BitacoraService {
  constructor(private readonly http: HttpClient) {}

  private construirParams(filtros: Partial<BitacoraFiltros>): HttpParams {
    let params = new HttpParams();
    if (filtros.usuarioId) params = params.set('usuario_id', filtros.usuarioId);
    if (filtros.modulo) params = params.set('modulo', filtros.modulo);
    if (filtros.accion) params = params.set('accion', filtros.accion);
    if (filtros.fechaDesde) params = params.set('fecha_desde', filtros.fechaDesde);
    if (filtros.fechaHasta) params = params.set('fecha_hasta', filtros.fechaHasta);
    return params;
  }

  private headers(token: string): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  listar(token: string, filtros: Partial<BitacoraFiltros>): Observable<BitacoraLog[]> {
    return this.http.get<BitacoraLog[]>(`${API_BASE}/bitacora`, {
      headers: this.headers(token),
      params: this.construirParams(filtros),
    });
  }

  exportar(token: string, formato: 'excel' | 'pdf', filtros: Partial<BitacoraFiltros>): Observable<Blob> {
    return this.http.get(`${API_BASE}/bitacora/export/${formato}`, {
      headers: this.headers(token),
      params: this.construirParams(filtros),
      responseType: 'blob',
    });
  }
}
