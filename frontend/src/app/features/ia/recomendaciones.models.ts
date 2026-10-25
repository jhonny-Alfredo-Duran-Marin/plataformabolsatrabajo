import { VacanteResumen } from '../../core/models/vacante.models';

/** Un criterio de la afinidad (HU-23, HU-24) y cuánto lo cumple el candidato. */
export interface CriterioAfinidad {
  clave: 'carrera' | 'habilidades' | 'experiencia' | 'idiomas' | string;
  nombre: string;
  peso: number;
  cumplimiento: number;
  estado: 'cumple' | 'parcial' | 'no_cumple' | string;
  detalle: string;
  coincidencias: string[];
  faltantes: string[];
}

/** HU-23: Vacante recomendada para el egresado */
export interface VacanteRecomendada {
  vacante: VacanteResumen;
  afinidad: number;
  criterios: CriterioAfinidad[];
  ya_postulado: boolean;
}

export interface Recomendaciones {
  calculado_en: string;
  total: number;
  perfil_faltantes: string[];
  items: VacanteRecomendada[];
}

/** HU-24: Candidato sugerido por afinidad para la empresa */
export interface CandidatoSugerido {
  candidate_id: string;
  user_id: string;
  application_id?: string | null;
  first_name: string;
  last_name: string;
  professional_headline?: string | null;
  carrera_principal?: string | null;
  city?: string | null;
  afinidad_porcentaje: number;
  nivel_coincidencia: string;
  razones_principales: string[];
  criterios: CriterioAfinidad[];
  current_status?: string | null;
  applied_at?: string | null;
}

export interface SugerenciasCandidatosResponse {
  vacante_id: string;
  vacante_titulo: string;
  calculado_en: string;
  umbral_minimo: number;
  total_postulantes: number;
  total_coincidentes: number;
  items: CandidatoSugerido[];
}

/** HU-28: Modelos del Chatbot de orientación */
export interface EnlaceUtilChatbot {
  texto: string;
  ruta: string;
}

export interface PostulacionResumenChatbot {
  application_id: string;
  job_id: string;
  job_title: string;
  company_name: string;
  current_status: string;
  status_label: string;
  etapa_actual?: string | null;
  applied_at: string;
}

export interface ChatbotMensaje {
  id: string;
  role: 'user' | 'assistant' | string;
  content: string;
  created_at: string;
  postulaciones?: PostulacionResumenChatbot[];
  enlaces_utiles?: EnlaceUtilChatbot[];
  en_alcance?: boolean;
}

export interface ChatbotSesionResponse {
  session_id: string;
  started_at: string;
  ended_at?: string | null;
  saludo: string;
  sugerencias: string[];
  mensajes: ChatbotMensaje[];
}

export interface ChatbotRespuestaResponse {
  session_id: string;
  mensaje_usuario: ChatbotMensaje;
  respuesta: ChatbotMensaje;
  intencion: string;
  en_alcance: boolean;
  postulaciones: PostulacionResumenChatbot[];
  sugerencias: string[];
  enlaces_utiles: EnlaceUtilChatbot[];
}
