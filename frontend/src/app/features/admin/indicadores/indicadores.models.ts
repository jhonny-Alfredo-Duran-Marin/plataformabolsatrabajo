export interface HabilidadDemanda {
  nombre: string;
  total: number;
  porcentaje: number;
}

export interface CarreraOpcion {
  id: string;
  nombre: string;
}

export interface FiltrosIndicadoresOpciones {
  carreras: CarreraOpcion[];
  periodos: string[];
}

export interface TableroIndicadores {
  fecha_actualizacion: string;
  carrera_id: string | null;
  carrera_nombre: string | null;
  periodo: string | null;
  hay_suficientes_datos: boolean;
  mensaje_insuficiente: string | null;
  total_egresados: number;
  total_colocaciones: number;
  total_encuestas_respondidas: number;
  tasa_colocacion: number | null;
  tiempo_promedio_primer_empleo_meses: number | null;
  pertinencia_empleo_porcentaje: number | null;
  habilidades_demandadas: HabilidadDemanda[];
}
