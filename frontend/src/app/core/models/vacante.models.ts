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
