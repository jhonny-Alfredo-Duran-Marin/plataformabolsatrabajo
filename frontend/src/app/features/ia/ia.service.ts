import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  ChatbotRespuestaResponse,
  ChatbotSesionResponse,
  Recomendaciones,
  SugerenciasCandidatosResponse,
  VacanteRecomendada,
} from './recomendaciones.models';

const BASE = `${environment.apiUrl}/ia`;

/** Módulos 5.1.11 a 5.1.13: Recomendación de vacantes (HU-23), Sugerencia de candidatos (HU-24) y Chatbot de orientación (HU-28). */
@Injectable({ providedIn: 'root' })
export class IaService {
  private readonly http = inject(HttpClient);

  /** Estado global del panel flotante del chatbot de orientación (HU-28). */
  readonly chatbotAbierto = signal(false);

  abrirChatbot(): void {
    this.chatbotAbierto.set(true);
  }

  cerrarChatbot(): void {
    this.chatbotAbierto.set(false);
  }

  alternarChatbot(): void {
    this.chatbotAbierto.update((v) => !v);
  }

  /** HU-23: Vacantes recomendadas por afinidad para el egresado. */
  recomendaciones(): Observable<Recomendaciones> {
    return this.http.get<Recomendaciones>(`${BASE}/recomendaciones`);
  }

  detalle(vacanteId: string): Observable<VacanteRecomendada> {
    return this.http.get<VacanteRecomendada>(`${BASE}/recomendaciones/${vacanteId}`);
  }

  /** HU-24: Ranking inteligente de candidatos sugeridos por afinidad para la empresa. */
  sugerenciasCandidatos(vacanteId: string, umbralMinimo = 0): Observable<SugerenciasCandidatosResponse> {
    const params = new HttpParams().set('umbral_minimo', umbralMinimo);
    return this.http.get<SugerenciasCandidatosResponse>(`${BASE}/sugerencias-candidatos/${vacanteId}`, {
      params,
    });
  }

  /** HU-28: Abre o recupera la sesión activa del chatbot de orientación del usuario autenticado. */
  abrirSesionChatbot(sessionId?: string | null): Observable<ChatbotSesionResponse> {
    let params = new HttpParams();
    if (sessionId) {
      params = params.set('session_id', sessionId);
    }
    return this.http.get<ChatbotSesionResponse>(`${BASE}/chatbot/sesion`, { params });
  }

  /** HU-28: Inicia una nueva sesión de conversación en el chatbot. */
  nuevaSesionChatbot(): Observable<ChatbotSesionResponse> {
    return this.http.post<ChatbotSesionResponse>(`${BASE}/chatbot/nueva-sesion`, {});
  }

  /** HU-28: Envía una pregunta en lenguaje natural al chatbot de orientación. */
  consultarChatbot(mensaje: string, sessionId?: string | null): Observable<ChatbotRespuestaResponse> {
    return this.http.post<ChatbotRespuestaResponse>(`${BASE}/chatbot/mensajes`, {
      mensaje,
      session_id: sessionId ?? null,
    });
  }
}
