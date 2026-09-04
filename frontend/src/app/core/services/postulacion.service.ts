import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Observable } from 'rxjs';

export interface ScreeningOption {
  id: string;
  option_text: string;
}

export interface ScreeningQuestion {
  id: string;
  question_text: string;
  question_type: string;
  is_required: boolean;
  options: ScreeningOption[];
}

export interface ApplicationAnswerCreate {
  question_id: string;
  selected_option_id?: string;
  answer_text?: string;
  answer_number?: number;
}

export interface PostulacionCreate {
  job_id: string;
  answers?: ApplicationAnswerCreate[];
}

export interface PostulacionResponse {
  id: string;
  job_id: string;
  current_status: string;
  message: string;
}

export interface PostulacionListResponse {
  id: string;
  job_id: string;
  job_title: string;
  company_name: string;
  current_status: string;
  applied_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class PostulacionService {
  private http = inject(HttpClient);
  private apiUrl = environment.apiUrl;

  // Obtener preguntas de filtro de una vacante
  getPreguntasFiltro(jobId: string): Observable<ScreeningQuestion[]> {
    return this.http.get<ScreeningQuestion[]>(`${this.apiUrl}/vacantes/${jobId}/preguntas`);
  }

  // Postularse a una vacante
  postularse(data: PostulacionCreate): Observable<PostulacionResponse> {
    return this.http.post<PostulacionResponse>(`${this.apiUrl}/postulaciones/`, data);
  }

  // Obtener mis postulaciones
  getMisPostulaciones(): Observable<PostulacionListResponse[]> {
    return this.http.get<PostulacionListResponse[]>(`${this.apiUrl}/postulaciones/`);
  }
}
