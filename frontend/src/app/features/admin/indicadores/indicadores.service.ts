import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { FiltrosIndicadoresOpciones, TableroIndicadores } from './indicadores.models';

@Injectable({ providedIn: 'root' })
export class IndicadoresService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/indicadores`;

  obtenerFiltros(): Observable<FiltrosIndicadoresOpciones> {
    return this.http.get<FiltrosIndicadoresOpciones>(`${this.base}/filtros`);
  }

  consultarTablero(carreraId?: string | null, periodo?: string | null): Observable<TableroIndicadores> {
    let params = new HttpParams();
    if (carreraId) {
      params = params.set('carrera_id', carreraId);
    }
    if (periodo && periodo.trim()) {
      params = params.set('periodo', periodo.trim());
    }
    return this.http.get<TableroIndicadores>(`${this.base}/tablero`, { params });
  }
}
