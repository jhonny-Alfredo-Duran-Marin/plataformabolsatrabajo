import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  CambioColocacion,
  Colocacion,
  ColocacionesPagina,
  EgresadoOpcion,
  EmpresaOpcion,
  FiltroColocaciones,
  NuevaColocacion,
} from './colocaciones.models';

/** HU-29: el administrador de la universidad registra, corrige y confirma las colocaciones de sus egresados. */
@Injectable({ providedIn: 'root' })
export class ColocacionesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/colocaciones`;

  listar(filtro: FiltroColocaciones): Observable<ColocacionesPagina> {
    let params = new HttpParams().set('page', filtro.page).set('page_size', filtro.pageSize);
    if (filtro.estado) params = params.set('estado', filtro.estado);
    if (filtro.q.trim()) params = params.set('q', filtro.q.trim());
    return this.http.get<ColocacionesPagina>(this.base, { params });
  }

  registrar(data: NuevaColocacion): Observable<Colocacion> {
    return this.http.post<Colocacion>(this.base, data);
  }

  editar(id: string, data: CambioColocacion): Observable<Colocacion> {
    return this.http.put<Colocacion>(`${this.base}/${id}`, data);
  }

  confirmar(id: string): Observable<Colocacion> {
    return this.http.post<Colocacion>(`${this.base}/${id}/confirmar`, {});
  }

  eliminar(id: string, motivo: string): Observable<Colocacion> {
    return this.http.request<Colocacion>('DELETE', `${this.base}/${id}`, { body: { motivo } });
  }

  buscarEgresados(q: string): Observable<EgresadoOpcion[]> {
    return this.http.get<EgresadoOpcion[]>(`${this.base}/egresados`, { params: new HttpParams().set('q', q.trim()) });
  }

  buscarEmpresas(q: string): Observable<EmpresaOpcion[]> {
    return this.http.get<EmpresaOpcion[]>(`${this.base}/empresas`, { params: new HttpParams().set('q', q.trim()) });
  }
}
