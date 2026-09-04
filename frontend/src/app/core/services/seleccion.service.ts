import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../features/auth/auth.service';
import {
  CandidatoTablero,
  ConfigurarEtapasRequest,
  DescartarCandidatoRequest,
  EtapaSeleccion,
  HistorialPostulacion,
  MoverCandidatoRequest,
  NotaInterna,
  NotaInternaRequest,
  TableroSeleccion,
} from '../models/seleccion.models';

@Injectable({
  providedIn: 'root',
})
export class SeleccionService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly apiUrl = `${environment.apiUrl}/seleccion`;

  private headers(): HttpHeaders {
    const token = this.auth.token();
    if (token) {
      return new HttpHeaders({ Authorization: `Bearer ${token}` });
    }
    return new HttpHeaders();
  }

  /** Obtiene el tablero Kanban con etapas y candidatos */
  obtenerTablero(vacanteId: string): Observable<TableroSeleccion> {
    return this.http.get<TableroSeleccion>(`${this.apiUrl}/vacantes/${vacanteId}/tablero`, {
      headers: this.headers(),
    });
  }

  /** Obtiene las etapas configuradas de una vacante */
  obtenerEtapas(vacanteId: string): Observable<EtapaSeleccion[]> {
    return this.http.get<EtapaSeleccion[]>(`${this.apiUrl}/vacantes/${vacanteId}/etapas`, {
      headers: this.headers(),
    });
  }

  /** Guarda o reordena la configuración de etapas */
  configurarEtapas(vacanteId: string, req: ConfigurarEtapasRequest): Observable<EtapaSeleccion[]> {
    return this.http.put<EtapaSeleccion[]>(`${this.apiUrl}/vacantes/${vacanteId}/etapas`, req, {
      headers: this.headers(),
    });
  }

  /** Mueve a un candidato de etapa con auditoría */
  moverCandidato(applicationId: string, req: MoverCandidatoRequest): Observable<CandidatoTablero> {
    return this.http.post<CandidatoTablero>(`${this.apiUrl}/postulaciones/${applicationId}/mover`, req, {
      headers: this.headers(),
    });
  }

  /** Descarta a un candidato en el proceso */
  descartarCandidato(applicationId: string, req: DescartarCandidatoRequest): Observable<CandidatoTablero> {
    return this.http.post<CandidatoTablero>(`${this.apiUrl}/postulaciones/${applicationId}/descartar`, req, {
      headers: this.headers(),
    });
  }

  /** Consulta el historial completo de auditoría de avances */
  obtenerHistorial(applicationId: string): Observable<HistorialPostulacion> {
    return this.http.get<HistorialPostulacion>(`${this.apiUrl}/postulaciones/${applicationId}/historial`, {
      headers: this.headers(),
    });
  }

  /** Consulta las notas internas privadas */
  obtenerNotas(applicationId: string): Observable<NotaInterna[]> {
    return this.http.get<NotaInterna[]>(`${this.apiUrl}/postulaciones/${applicationId}/notas`, {
      headers: this.headers(),
    });
  }

  /** Registra una nueva nota interna */
  registrarNota(applicationId: string, req: NotaInternaRequest): Observable<NotaInterna> {
    return this.http.post<NotaInterna>(`${this.apiUrl}/postulaciones/${applicationId}/notas`, req, {
      headers: this.headers(),
    });
  }
}

