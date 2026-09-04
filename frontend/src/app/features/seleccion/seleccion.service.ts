import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  AvanzarEtapaRequest,
  CandidatoPipelineItem,
  ConfigurarEtapasRequest,
  DescartarCandidatoRequest,
  EtapaResponse,
  NotaInternaRequest,
  NotaInternaResponse,
  PipelineVacanteResponse,
  VacanteResumenSeleccion,
} from './seleccion.models';

@Injectable({ providedIn: 'root' })
export class SeleccionService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/seleccion`;


  listarVacantes(): Observable<VacanteResumenSeleccion[]> {
    return this.http.get<VacanteResumenSeleccion[]>(`${this.base}/vacantes`);
  }

  obtenerEtapas(idVacante: string): Observable<EtapaResponse[]> {
    return this.http.get<EtapaResponse[]>(`${this.base}/vacantes/${idVacante}/etapas`);
  }

  configurarEtapas(idVacante: string, data: ConfigurarEtapasRequest): Observable<EtapaResponse[]> {
    return this.http.put<EtapaResponse[]>(`${this.base}/vacantes/${idVacante}/etapas`, data);
  }

  obtenerPipeline(idVacante: string): Observable<PipelineVacanteResponse> {
    return this.http.get<PipelineVacanteResponse>(`${this.base}/vacantes/${idVacante}/pipeline`);
  }

  avanzarEtapa(idPostulacion: string, data: AvanzarEtapaRequest): Observable<CandidatoPipelineItem> {
    return this.http.post<CandidatoPipelineItem>(`${this.base}/postulaciones/${idPostulacion}/avanzar`, data);
  }

  descartarCandidato(idPostulacion: string, data: DescartarCandidatoRequest): Observable<CandidatoPipelineItem> {
    return this.http.post<CandidatoPipelineItem>(`${this.base}/postulaciones/${idPostulacion}/descartar`, data);
  }

  listarNotas(idPostulacion: string): Observable<NotaInternaResponse[]> {
    return this.http.get<NotaInternaResponse[]>(`${this.base}/postulaciones/${idPostulacion}/notas`);
  }

  agregarNota(idPostulacion: string, data: NotaInternaRequest): Observable<NotaInternaResponse> {
    return this.http.post<NotaInternaResponse>(`${this.base}/postulaciones/${idPostulacion}/notas`, data);
  }
}
