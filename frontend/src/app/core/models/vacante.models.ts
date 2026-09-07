export type SeniorityLevel = 'internship' | 'junior' | 'mid' | 'senior' | 'lead';

export type EmploymentType =
  | 'permanent'
  | 'temporary'
  | 'contract'
  | 'internship'
  | 'part_time'
  | 'freelance';

export type WorkModality = 'onsite' | 'remote' | 'hybrid';

export type JobStatus =
  | 'draft'
  | 'pending_review'
  | 'published'
  | 'paused'
  | 'closed'
  | 'rejected'
  | 'archived';

export type SkillProficiencyLevel = 'basic' | 'intermediate' | 'advanced' | 'expert';

export type SkillImportance = 'required' | 'preferred' | 'optional';

export interface JobSkillItemRequest {
  skill_id: string;
  importance?: SkillImportance | null;
  min_proficiency?: SkillProficiencyLevel | null;
  weight?: number | null;
}

export interface JobSkillItemResponse {
  skill_id: string;
  skill_name?: string | null;
  importance?: string | null;
  min_proficiency?: string | null;
  weight?: number | null;
}

export interface Vacante {
  id: string;
  company_id: string;
  company_name?: string | null;
  created_by?: string | null;
  category_id?: string | null;
  category_name?: string | null;
  title: string;
  description: string;
  responsibilities_json?: string[] | null;
  requirements_json?: string[] | null;
  benefits_json?: string[] | null;
  seniority_level: SeniorityLevel | string;
  employment_type: EmploymentType | string;
  work_modality: WorkModality | string;
  min_education_level?: string | null;
  min_years_experience?: number | null;
  country_code: string;
  city: string;
  latitude?: number | null;
  longitude?: number | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
  salary_visible: boolean;
  positions_available: number;
  status: JobStatus | string;
  rejection_reason?: string | null;
  application_deadline?: string | null;
  published_at?: string | null;
  closed_at?: string | null;
  view_count: number;
  created_at: string;
  updated_at: string;
  skills: JobSkillItemResponse[];
}

export interface VacanteCreateRequest {
  title: string;
  description: string;
  responsibilities_json?: string[] | null;
  requirements_json?: string[] | null;
  benefits_json?: string[] | null;
  category_id?: string | null;
  seniority_level: SeniorityLevel;
  employment_type: EmploymentType;
  work_modality?: WorkModality;
  min_education_level?: string | null;
  min_years_experience?: number | null;
  country_code?: string;
  city: string;
  latitude?: number | null;
  longitude?: number | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string;
  salary_visible?: boolean;
  positions_available?: number;
  status?: JobStatus;
  application_deadline?: string | null;
  skills?: JobSkillItemRequest[];
}

export interface VacanteUpdateRequest {
  title?: string;
  description?: string;
  responsibilities_json?: string[] | null;
  requirements_json?: string[] | null;
  benefits_json?: string[] | null;
  category_id?: string | null;
  seniority_level?: SeniorityLevel | null;
  employment_type?: EmploymentType | null;
  work_modality?: WorkModality | null;
  min_education_level?: string | null;
  min_years_experience?: number | null;
  country_code?: string | null;
  city?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
  salary_visible?: boolean | null;
  positions_available?: number | null;
  status?: JobStatus | null;
  application_deadline?: string | null;
  skills?: JobSkillItemRequest[] | null;
}

export interface VacanteCambioEstadoRequest {
  status: JobStatus;
}

export interface VacanteModeracionRequest {
  aprobado: boolean;
  motivo_rechazo?: string | null;
}

export interface VacantePaginadaResponse {
  items: Vacante[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface VacanteFiltros {
  q?: string;
  category_id?: string;
  city?: string;
  work_modality?: string;
  seniority_level?: string;
  employment_type?: string;
  salary_min?: number;
  estado?: string;
  page?: number;
  page_size?: number;
}

// ─── Búsqueda avanzada con afinidad (HU-13) ─────────────────────────────────
// Tipos usados por GET /vacantes/buscar, separado del listado simple de arriba.

export interface EmpresaEnVacante {
  id: string;
  legal_name: string;
  trade_name?: string | null;
  city?: string | null;
  sector_name?: string | null;
  website?: string | null;
  description?: string | null;
}

export interface HabilidadEnVacante {
  skill_id: string;
  name: string;
  importance: string; // 'required' | 'preferred'
  min_proficiency?: string | null;
}

export interface CarreraEnVacante {
  field_of_study_id: string;
  name: string;
  education_level?: string | null;
  is_required: boolean;
}

export interface VacanteResumen {
  id: string;
  company: EmpresaEnVacante;
  category_id?: string | null;
  category_name?: string | null;
  title: string;
  description: string;
  seniority_level: string;
  employment_type: string;
  work_modality: string;
  country_code: string;
  city: string;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
  salary_visible: boolean;
  positions_available: number;
  status: string;
  min_education_level?: string | null;
  min_years_experience?: number | null;
  application_deadline?: string | null;
  published_at?: string | null;
  view_count: number;
  skills: HabilidadEnVacante[];
  education_preferences: CarreraEnVacante[];
  afinidad_porcentaje?: number | null;
}

export interface VacanteDetalle extends VacanteResumen {
  responsibilities: string[];
  requirements: string[];
  benefits: string[];
  company_contact_email?: string | null;
  company_phone?: string | null;
  company_address?: string | null;
}

export interface CategoriaFiltro {
  id: string;
  name: string;
}

export interface CarreraFiltro {
  id: string;
  name: string;
  category?: string | null;
}

export interface FiltrosDisponibles {
  ciudades: string[];
  modalidades: string[];
  jornadas: string[];
  niveles_experiencia: string[];
  categorias: CategoriaFiltro[];
  carreras: CarreraFiltro[];
  salario_min_disponible?: number | null;
  salario_max_disponible?: number | null;
}

export interface VacantesPaginadas {
  total: number;
  limit: number;
  offset: number;
  items: VacanteResumen[];
}

// ─── Preguntas de filtro (screening) — HU-11 ────────────────────────────────

export interface PreguntaFiltroOpcion {
  id?: string;
  option_text: string;
  is_accepted: boolean;
  position: number;
}

export interface PreguntaFiltro {
  id: string;
  job_posting_id: string;
  question_text: string;
  question_type: 'text' | 'number' | 'single_choice';
  is_required: boolean;
  is_knockout: boolean;
  position: number;
  options: PreguntaFiltroOpcion[];
}

export interface PreguntaFiltroCreateRequest {
  question_text: string;
  question_type: 'text' | 'number' | 'single_choice';
  is_required: boolean;
  is_knockout: boolean;
  position: number;
  options: PreguntaFiltroOpcion[];
}

export interface PreguntaFiltroUpdateRequest {
  question_text?: string;
  is_required?: boolean;
  is_knockout?: boolean;
  position?: number;
  options?: PreguntaFiltroOpcion[];
}

export interface FiltrosBusquedaVacantes {
  q?: string;
  carrera_id?: string;
  categoria_id?: string;
  ciudad?: string;
  modalidad?: string;
  jornada?: string;
  seniority?: string;
  salario_min?: number;
  salario_max?: number;
  ordenar_por?: 'fecha' | 'afinidad';
  limit?: number;
  offset?: number;
}
