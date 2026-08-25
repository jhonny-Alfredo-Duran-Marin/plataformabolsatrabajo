export type EstadoVerificacionEmpresa =
  | 'PENDIENTE'
  | 'VERIFICADA'
  | 'RECHAZADA'
  | 'SUSPENDIDA';

export interface Empresa {
  id: string;
  usuario_id: string | null;
  razon_social: string;
  nit: string;
  sector?: string;
  tamanio?: string;
  direccion?: string;
  telefono?: string;
  sitio_web?: string;
  descripcion?: string;
  representante_legal?: string;
  estado_verificacion: EstadoVerificacionEmpresa;
  motivo_rechazo?: string;
  notificaciones_activas: boolean;
  postulaciones_activas: boolean;
  activo: boolean;
  fecha_registro?: string;
  fecha_eliminacion?: string;
}

export interface ConfiguracionEmpresaRequest {
  notificaciones_activas?: boolean;
  postulaciones_activas?: boolean;
}

