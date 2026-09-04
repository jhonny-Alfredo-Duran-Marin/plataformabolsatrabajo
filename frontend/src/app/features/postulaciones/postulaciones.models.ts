export interface HabilidadItem {
  nombre: string;
  importancia?: string | null;
  nivel_minimo?: string | null;
}

export interface PostulacionItem {
  id: string;
  job_id: string;
  job_titulo: string;
  empresa_id: string;
  empresa_nombre: string;
  empresa_ciudad?: string | null;
  modalidad: string;
  modalidad_label: string;
  tipo_empleo: string;
  tipo_empleo_label: string;
  salario_min?: number | null;
  salario_max?: number | null;
  currency?: string | null;
  salario_visible: boolean;
  estado: string;
  estado_label: string;
  estado_color: string;
  etapa_actual_nombre?: string | null;
  fecha_postulacion: string;
  fecha_ultimo_cambio: string;
  cover_letter?: string | null;
  puede_retirar: boolean;
}

export interface HistorialEstado {
  id: string;
  desde_estado?: string | null;
  desde_estado_label?: string | null;
  hacia_estado: string;
  hacia_estado_label: string;
  hacia_estado_color: string;
  motivo?: string | null;
  fecha: string;
}

export interface EtapaHistorial {
  id: string;
  etapa_nombre: string;
  etapa_numero?: number | null;
  resultado?: string | null;
  resultado_label?: string | null;
  notas?: string | null;
  fecha_ingreso: string;
  fecha_salida?: string | null;
}

export interface DetalleVacante {
  id: string;
  titulo: string;
  descripcion: string;
  empresa_id: string;
  empresa_nombre: string;
  empresa_rubro?: string | null;
  empresa_tamano?: string | null;
  empresa_descripcion?: string | null;
  ciudad?: string | null;
  pais?: string | null;
  modalidad: string;
  modalidad_label: string;
  tipo_empleo: string;
  tipo_empleo_label: string;
  seniority?: string | null;
  anios_experiencia_min?: number | null;
  nivel_educativo_min?: string | null;
  salario_min?: number | null;
  salario_max?: number | null;
  currency?: string | null;
  salario_visible: boolean;
  posiciones_disponibles: number;
  habilidades: HabilidadItem[];
  fecha_publicacion?: string | null;
  fecha_limite?: string | null;
}

export interface DetallePostulacion {
  postulacion: PostulacionItem;
  vacante: DetalleVacante;
  historial_estados: HistorialEstado[];
  historial_etapas: EtapaHistorial[];
}

export interface ResumenPostulaciones {
  total: number;
  activas: number;
  en_revision: number;
  entrevistas_ofertas: number;
  contratados: number;
  finalizadas: number;
  postulaciones: PostulacionItem[];
}

export interface FiltroPostulaciones {
  estado?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  busqueda?: string;
}
