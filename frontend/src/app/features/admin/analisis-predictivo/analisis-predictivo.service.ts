import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { BrechaHabilidades, FiltrosBrecha } from './analisis-predictivo.models';

/** HU-33: el administrador consulta la brecha de habilidades de una carrera. */
@Injectable({ providedIn: 'root' })
export class AnalisisPredictivoService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/ia/analisis-predictivo`;

  filtros(): Observable<FiltrosBrecha> {
    return this.http.get<FiltrosBrecha>(`${this.base}/filtros`);
  }

  brechaHabilidades(carreraId: string, periodo: string | null): Observable<BrechaHabilidades> {
    let params = new HttpParams().set('carrera_id', carreraId);
    if (periodo) params = params.set('periodo', periodo);
    return this.http.get<BrechaHabilidades>(`${this.base}/brecha-habilidades`, { params });
  }
}
