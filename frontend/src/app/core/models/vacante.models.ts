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

