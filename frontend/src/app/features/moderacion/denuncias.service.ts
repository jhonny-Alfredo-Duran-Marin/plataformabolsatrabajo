import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  CategoriaDenuncia,
  DecisionDenuncia,
  DenunciaCreada,
  DenunciasPendientes,
  MiDenuncia,
  ResolucionDenuncia,
} from './denuncias.models';

/** HU-22: denunciar una oferta y, para el administrador, revisar las denuncias. */
@Injectable({ providedIn: 'root' })
export class DenunciasService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/moderacion`;

  denunciar(
    vacanteId: string,
    categoria: CategoriaDenuncia,
    descripcion: string | null,
  ): Observable<DenunciaCreada> {
    return this.http.post<DenunciaCreada>(`${this.base}/vacantes/${vacanteId}/denuncias`, {
      categoria,
      descripcion,
    });
  }

  miDenuncia(vacanteId: string): Observable<MiDenuncia> {
    return this.http.get<MiDenuncia>(`${this.base}/vacantes/${vacanteId}/mi-denuncia`);
  }

  listarPendientes(page: number, pageSize: number): Observable<DenunciasPendientes> {
    const params = new HttpParams().set('page', page).set('page_size', pageSize);
    return this.http.get<DenunciasPendientes>(`${this.base}/denuncias`, { params });
  }

  resolver(
    vacanteId: string,
    decision: DecisionDenuncia,
    nota: string | null,
  ): Observable<ResolucionDenuncia> {
    return this.http.post<ResolucionDenuncia>(`${this.base}/vacantes/${vacanteId}/resolucion`, {
      decision,
      nota,
    });
  }
}
