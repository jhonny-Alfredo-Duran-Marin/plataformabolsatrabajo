export interface EtapaItem {
  id?: string | null;
  stage_number: number;
  name: string;
  description?: string | null;
  is_terminal: boolean;
  total_candidatos?: number;
}

export interface EtapaResponse {
  id: string;
  job_posting_id: string;
  stage_number: number;
  name: string;
  description?: string | null;
  is_terminal: boolean;
  total_candidatos: number;
}

export interface VacanteResumenSeleccion {
  id: string;
  titulo: string;
  seniority?: string | null;
  modalidad: string;
  modalidad_label: string;
  tipo_empleo: string;
  tipo_empleo_label: string;
  total_postulantes: number;
  total_activos: number;
  total_descartados: number;
  total_contratados: number;
}

export interface CandidatoPipelineItem {
  postulacion_id: string;
  candidato_id: string;
  candidato_nombre: string;
  candidato_titular?: string | null;
  candidato_carrera?: string | null;
  candidato_email?: string | null;
  candidato_telefono?: string | null;
  candidato_ciudad?: string | null;
  estado: string;
  estado_label: string;
  estado_color: string;
  etapa_actual_id?: string | null;
  etapa_actual_nombre?: string | null;
  etapa_actual_numero?: number | null;
  fecha_postulacion: string;
  fecha_ultimo_cambio: string;
  total_notas: number;
  puede_avanzar: boolean;
  puede_descartar: boolean;
}

export interface PipelineVacanteResponse {
  vacante: VacanteResumenSeleccion;
  etapas: EtapaResponse[];
  candidatos: CandidatoPipelineItem[];
}

export interface AvanzarEtapaRequest {
  stage_id: string;
  observacion?: string | null;
}

export interface DescartarCandidatoRequest {
  motivo?: string | null;
}

export interface NotaInternaRequest {
  content: string;
}

export interface NotaInternaResponse {
  id: string;
  postulacion_id: string;
  autor_nombre: string;
  autor_cargo?: string | null;
  content: string;
  created_at: string;
}

export interface ConfigurarEtapasRequest {
  etapas: EtapaItem[];
}
