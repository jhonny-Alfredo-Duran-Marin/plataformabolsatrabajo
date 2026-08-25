export type EstadoValidacionEgresado = 'PENDIENTE' | 'APROBADO' | 'RECHAZADO';

export interface PerfilEgresado {
  id: string;
  usuario_id: string;
  nombres: string;
  apellidos: string;
  ci: string | null;
  telefono: string | null;
  direccion: string | null;
  fecha_nacimiento: string | null;
  carrera_id: string | null;
  anio_egreso: number | null;
  matricula: string | null;
  estado_validacion: EstadoValidacionEgresado;
  porcentaje_completitud: number;
  perfil_oculto: boolean;
}

export interface Carrera {
  id: string;
  nombre: string;
  facultad: string | null;
}

export interface ValidacionDecisionRequest {
  aprobado: boolean;
  motivo_rechazo?: string | null;
}
