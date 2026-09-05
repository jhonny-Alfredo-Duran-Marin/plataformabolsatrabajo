import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../features/auth/auth.service';
import { ConfiguracionEmpresaRequest, DecisionEmpresaRequest, Empresa } from '../models/empresa.models';

@Injectable({
  providedIn: 'root',
})
export class EmpresaService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly apiUrl = `${environment.apiUrl}/validacion/empresas`;

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.token()}` });
  }

  /** Lista todas las empresas con opción de incluir empresas desactivadas lógicamente */
  listarEmpresas(incluirInactivas: boolean = true): Observable<Empresa[]> {
    const params = new HttpParams().set('incluir_inactivas', String(incluirInactivas));
    return this.http.get<Empresa[]>(this.apiUrl, { headers: this.headers(), params });
  }

  /** Aprueba o rechaza la verificación de una empresa (HU-06) */
  decidir(empresaId: string, decision: DecisionEmpresaRequest): Observable<Empresa> {
    return this.http.post<Empresa>(`${this.apiUrl}/${empresaId}/decision`, decision, {
      headers: this.headers(),
    });
  }

  /** Actualiza los permisos de notificaciones o postulaciones de la empresa */
  actualizarConfiguracion(empresaId: string, config: ConfiguracionEmpresaRequest): Observable<Empresa> {
    return this.http.patch<Empresa>(`${this.apiUrl}/${empresaId}/configuracion`, config, {
      headers: this.headers(),
    });
  }

  /** Ejecuta la baja lógica (Soft delete) de la empresa */
  eliminarLogico(empresaId: string): Observable<Empresa> {
    return this.http.delete<Empresa>(`${this.apiUrl}/${empresaId}`, { headers: this.headers() });
  }

  /** Restaura una empresa que fue desactivada lógicamente */
  restaurar(empresaId: string): Observable<Empresa> {
    return this.http.post<Empresa>(`${this.apiUrl}/${empresaId}/restaurar`, {}, { headers: this.headers() });
  }
}
