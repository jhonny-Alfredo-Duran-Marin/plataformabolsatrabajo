import { HttpClient, HttpParams, HttpResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  CatalogoReportes,
  ConsultaReporte,
  EnvioReporte,
  FormatoReporte,
  ReporteInterpretado,
  VistaPrevia,
} from './reportes.models';

/** Reportes personalizados (requisito 5): universidades, superadmin y empresas. */
@Injectable({ providedIn: 'root' })
export class ReportesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/reportes`;

  catalogo(): Observable<CatalogoReportes> {
    return this.http.get<CatalogoReportes>(`${this.base}/fuentes`);
  }

  /** Arma la consulta a partir de un pedido en lenguaje natural (escrito o dictado). */
  interpretar(pedido: string): Observable<ReporteInterpretado> {
    return this.http.post<ReporteInterpretado>(`${this.base}/interpretar`, { pedido });
  }

  vistaPrevia(consulta: ConsultaReporte, pagina: number, tamanio: number): Observable<VistaPrevia> {
    const params = new HttpParams().set('pagina', pagina).set('tamanio', tamanio);
    return this.http.post<VistaPrevia>(`${this.base}/vista-previa`, consulta, { params });
  }

  exportar(consulta: ConsultaReporte, formato: FormatoReporte): Observable<HttpResponse<Blob>> {
    return this.http.post(
      `${this.base}/exportar`,
      { ...consulta, formato },
      { observe: 'response', responseType: 'blob' },
    );
  }

  enviar(
    consulta: ConsultaReporte,
    formato: FormatoReporte,
    destinatarios: string[],
    mensaje: string | null,
  ): Observable<EnvioReporte> {
    return this.http.post<EnvioReporte>(`${this.base}/enviar`, {
      ...consulta,
      formato,
      destinatarios,
      mensaje,
    });
  }

  /** HU-31: Tablero consolidado de indicadores de inserción laboral. */
  indicadores(carreraId?: string, periodo?: string): Observable<any> {
    let params = new HttpParams();
    if (carreraId) params = params.set('carrera_id', carreraId);
    if (periodo) params = params.set('periodo', periodo);
    return this.http.get<any>(`${environment.apiUrl}/indicators`, { params });
  }

  /** HU-32: Exportación del tablero de indicadores a PDF o Excel. */
  exportarIndicadores(formato: 'pdf' | 'xlsx', carreraId?: string, periodo?: string): Observable<HttpResponse<Blob>> {
    let params = new HttpParams().set('format', formato);
    if (carreraId) params = params.set('carrera_id', carreraId);
    if (periodo) params = params.set('periodo', periodo);
    return this.http.get(`${environment.apiUrl}/indicators/export`, {
      params,
      observe: 'response',
      responseType: 'blob',
    });
  }
}
