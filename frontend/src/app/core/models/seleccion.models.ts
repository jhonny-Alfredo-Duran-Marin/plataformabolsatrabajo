export interface EtapaSeleccion {
  id: string;
  job_posting_id: string;
  stage_number: number;
  name: string;
  description?: string | null;
  is_terminal: boolean;
  created_at: string;
}

export interface EtapaItemRequest {
  id?: string | null;
  stage_number: number;
  name: string;
  description?: string | null;
  is_terminal: boolean;
}

export interface ConfigurarEtapasRequest {
  etapas: EtapaItemRequest[];
}

export interface CandidatoTablero {
  application_id: string;
  candidate_id: string;
  user_id?: string | null;
  first_name: string;
  last_name: string;
  email?: string | null;
  phone?: string | null;
  city?: string | null;
  professional_headline?: string | null;
  current_stage_id?: string | null;
  current_status: string;
  applied_at: string;
  notas_count: number;
  cover_letter?: string | null;
  afinidad_porcentaje?: number | null;
}

export interface ColumnaEtapaTablero {
  stage: EtapaSeleccion;
  candidatos: CandidatoTablero[];
}

export interface TableroSeleccion {
  job_posting_id: string;
  job_title: string;
  company_id: string;
  company_name: string;
  total_candidatos: number;
  columnas: ColumnaEtapaTablero[];
  candidatos_descartados: CandidatoTablero[];
}

export interface MoverCandidatoRequest {
  nueva_etapa_id: string;
  observacion?: string | null;
}

export interface DescartarCandidatoRequest {
  motivo?: string | null;
}

export interface HistorialEtapaItem {
  id: string;
  stage_id: string;
  stage_name: string;
  entered_at: string;
  left_at?: string | null;
  changed_by_id?: string | null;
  changed_by_name?: string | null;
  result?: string | null;
  notes?: string | null;
}

export interface HistorialPostulacion {
  application_id: string;
  current_status: string;
  historial: HistorialEtapaItem[];
}

export interface NotaInterna {
  id: string;
  application_id: string;
  author_id: string;
  author_name: string;
  content: string;
  created_at: string;
}

export interface NotaInternaRequest {
  content: string;
}

