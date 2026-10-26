import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AvanceEncuesta,
  Encuesta,
  EncuestaCreada,
  EncuestasPagina,
  FormularioEncuesta,
  MiEncuesta,
  NuevaEncuesta,
  RespuestaCreada,
  RespuestaPregunta,
} from './encuestas.models';

/** HU-30: el administrador envía la encuesta y sigue su avance; el egresado la responde. */
@Injectable({ providedIn: 'root' })
export class EncuestasService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/encuestas`;

  // ─── Administrador universitario ─────────────────────────────────────

  enviar(data: NuevaEncuesta): Observable<EncuestaCreada> {
    return this.http.post<EncuestaCreada>(this.base, data);
  }

  listar(page: number, pageSize: number): Observable<EncuestasPagina> {
    const params = new HttpParams().set('page', page).set('page_size', pageSize);
    return this.http.get<EncuestasPagina>(this.base, { params });
  }

  avance(id: string): Observable<AvanceEncuesta> {
    return this.http.get<AvanceEncuesta>(`${this.base}/${id}/avance`);
  }

  cerrar(id: string): Observable<Encuesta> {
    return this.http.post<Encuesta>(`${this.base}/${id}/cerrar`, {});
  }

  // ─── Egresado ────────────────────────────────────────────────────────

  mias(): Observable<MiEncuesta[]> {
    return this.http.get<MiEncuesta[]>(`${this.base}/mias`);
  }

  formulario(id: string): Observable<FormularioEncuesta> {
    return this.http.get<FormularioEncuesta>(`${this.base}/${id}/formulario`);
  }

  responder(id: string, respuestas: RespuestaPregunta[]): Observable<RespuestaCreada> {
    return this.http.post<RespuestaCreada>(`${this.base}/${id}/respuestas`, { respuestas });
  }
}
