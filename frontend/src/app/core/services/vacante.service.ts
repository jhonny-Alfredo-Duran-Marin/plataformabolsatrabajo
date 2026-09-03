import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../features/auth/auth.service';
import {
  FiltrosBusquedaVacantes,
  FiltrosDisponibles,
  VacanteDetalle,
  VacantesPaginadas,
} from '../models/vacante.models';

@Injectable({
  providedIn: 'root',
})
export class VacanteService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly apiUrl = `${environment.apiUrl}/vacantes`;

  private headers(): HttpHeaders {
    const token = this.auth.token();
    if (token) {
      return new HttpHeaders({ Authorization: `Bearer ${token}` });
    }
    return new HttpHeaders();
  }

  /** Busca vacantes aplicando filtros combinados y paginación */
  buscarVacantes(filtros: FiltrosBusquedaVacantes = {}): Observable<VacantesPaginadas> {
    let params = new HttpParams();

    if (filtros.q && filtros.q.trim()) {
      params = params.set('q', filtros.q.trim());
    }
    if (filtros.carrera_id) {
      params = params.set('carrera_id', filtros.carrera_id);
    }
    if (filtros.categoria_id) {
      params = params.set('categoria_id', filtros.categoria_id);
    }
    if (filtros.ciudad) {
      params = params.set('ciudad', filtros.ciudad);
    }
    if (filtros.modalidad) {
      params = params.set('modalidad', filtros.modalidad);
    }
    if (filtros.jornada) {
      params = params.set('jornada', filtros.jornada);
    }
    if (filtros.seniority) {
      params = params.set('seniority', filtros.seniority);
    }
    if (filtros.salario_min !== undefined && filtros.salario_min !== null) {
      params = params.set('salario_min', String(filtros.salario_min));
    }
    if (filtros.salario_max !== undefined && filtros.salario_max !== null) {
      params = params.set('salario_max', String(filtros.salario_max));
    }
    if (filtros.ordenar_por) {
      params = params.set('ordenar_por', filtros.ordenar_por);
    }
    if (filtros.limit !== undefined) {
      params = params.set('limit', String(filtros.limit));
    }
    if (filtros.offset !== undefined) {
      params = params.set('offset', String(filtros.offset));
    }

    return this.http.get<VacantesPaginadas>(this.apiUrl, {
      headers: this.headers(),
      params,
    });
  }

  /** Obtiene las opciones de catálogo dinámicas para los filtros */
  obtenerFiltrosDisponibles(): Observable<FiltrosDisponibles> {
    return this.http.get<FiltrosDisponibles>(`${this.apiUrl}/filtros`, {
      headers: this.headers(),
    });
  }

  /** Obtiene el detalle completo de una vacante */
  obtenerDetalle(vacanteId: string): Observable<VacanteDetalle> {
    return this.http.get<VacanteDetalle>(`${this.apiUrl}/${vacanteId}`, {
      headers: this.headers(),
    });
  }
}

