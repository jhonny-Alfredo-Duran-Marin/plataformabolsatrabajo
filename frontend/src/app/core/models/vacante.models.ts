export type SeniorityLevel =
  | 'internship'
  | 'junior'
  | 'mid'
  | 'senior'
  | 'lead'
  | 'manager';

export type EmploymentType =
  | 'permanent'
  | 'temporary'
  | 'project'
  | 'internship'
  | 'freelance';

export type WorkModality = 'onsite' | 'remote' | 'hybrid';

export type JobStatus =
  | 'draft'
  | 'pending_review'
  | 'published'
  | 'paused'
  | 'closed'
  | 'rejected';

export type SkillProficiencyLevel =
  | 'basic'
  | 'intermediate'
  | 'advanced'
  | 'expert';

export interface JobSkillItemRequest {
  skill_id: string;
  required_level?: SkillProficiencyLevel | null;
  is_required: boolean;
  weight?: number | null;
}

export interface JobSkillItemResponse {
  skill_id: string;
  skill_name?: string | null;
  required_level?: string | null;
  is_required: boolean;
  weight?: number | null;
}

export interface Vacante {
  id: string;
  company_id: string;
  company_name?: string | null;
  created_by_member_id?: string | null;
  category_id?: string | null;
  category_name?: string | null;
  title: string;
  description: string;
  responsibilities?: string | null;
  requirements?: string | null;
  seniority_level?: SeniorityLevel | string | null;
  employment_type?: EmploymentType | string | null;
  work_modality?: WorkModality | string | null;
  minimum_education_level?: string | null;
  required_experience_years?: number | null;
  country_code?: string | null;
  city?: string | null;
  location_text?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
  salary_visible: boolean;
  positions_count: number;
  status: JobStatus | string;
  published_at?: string | null;
  closes_at?: string | null;
  created_at: string;
  updated_at: string;
  skills: JobSkillItemResponse[];
}

export interface VacanteCreateRequest {
  title: string;
  description: string;
  responsibilities?: string | null;
  requirements?: string | null;
  category_id?: string | null;
  seniority_level?: SeniorityLevel | null;
  employment_type?: EmploymentType | null;
  work_modality?: WorkModality;
  minimum_education_level?: string | null;
  required_experience_years?: number | null;
  country_code?: string;
  city?: string | null;
  location_text?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string;
  salary_visible?: boolean;
  positions_count?: number;
  status?: JobStatus;
  closes_at?: string | null;
  skills?: JobSkillItemRequest[];
}

export interface VacanteUpdateRequest {
  title?: string;
  description?: string;
  responsibilities?: string | null;
  requirements?: string | null;
  category_id?: string | null;
  seniority_level?: SeniorityLevel | null;
  employment_type?: EmploymentType | null;
  work_modality?: WorkModality | null;
  minimum_education_level?: string | null;
  required_experience_years?: number | null;
  country_code?: string | null;
  city?: string | null;
  location_text?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
  salary_visible?: boolean | null;
  positions_count?: number | null;
  status?: JobStatus | null;
  closes_at?: string | null;
  skills?: JobSkillItemRequest[] | null;
}

export interface VacanteCambioEstadoRequest {
  status: JobStatus;
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
