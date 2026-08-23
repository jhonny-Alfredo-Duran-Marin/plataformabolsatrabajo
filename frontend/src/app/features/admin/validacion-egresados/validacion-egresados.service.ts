import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { Carrera, PerfilEgresado, ValidacionDecisionRequest } from './validacion-egresados.model';

// TODO: mover a environments/ cuando se configure el flujo de build por entorno.
const API_BASE = 'http://localhost:8000/api';

@Injectable({ providedIn: 'root' })
export class ValidacionEgresadosService {
  constructor(private readonly http: HttpClient) {}

  private headers(token: string): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  listarPendientes(token: string): Observable<PerfilEgresado[]> {
    return this.http.get<PerfilEgresado[]>(`${API_BASE}/validacion/egresados/pendientes`, {
      headers: this.headers(token),
    });
  }

  decidir(token: string, perfilId: number, data: ValidacionDecisionRequest): Observable<PerfilEgresado> {
    return this.http.post<PerfilEgresado>(
      `${API_BASE}/validacion/egresados/${perfilId}/decision`,
      data,
      { headers: this.headers(token) },
    );
  }

  listarCarreras(): Observable<Carrera[]> {
    return this.http.get<Carrera[]>(`${API_BASE}/catalogos/carreras`);
  }
}
