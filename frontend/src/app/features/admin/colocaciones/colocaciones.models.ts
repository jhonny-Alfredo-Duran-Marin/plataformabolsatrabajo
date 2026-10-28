/** HU-29: registro de colocaciones (contrataciones de egresados) de cada universidad. */

export type EstadoColocacion = 'suggested' | 'confirmed' | 'cancelled';
export type OrigenColocacion = 'platform' | 'manual';

export const ESTADO_LEGIBLE: Record<EstadoColocacion, string> = {
  suggested: 'Por confirmar',
  confirmed: 'Confirmada',
  cancelled: 'Eliminada',
};

export const ORIGEN_LEGIBLE: Record<OrigenColocacion, string> = {
  platform: 'Sugerida por la plataforma',
  manual: 'Registro manual',
};

export interface Colocacion {
  id: string;
  egresado_id: string;
  egresado: string;
  universidad_id: string;
  universidad: string | null;
  empresa_id: string | null;
  empresa: string;
  cargo: string;
  /** AAAA-MM-DD */
  fecha_inicio: string;
  salario: number | string | null;
  moneda: string | null;
  estado: EstadoColocacion;
  origen: OrigenColocacion;
  postulacion_id: string | null;
  motivo_ultimo_cambio: string | null;
  eliminada_el: string | null;
  motivo_eliminacion: string | null;
  registrada_el: string;
  actualizada_el: string;
}

export interface ColocacionesPagina {
  items: Colocacion[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  /** Sugeridas que esperan confirmación, sin contar los filtros. */
  sugeridas: number;
}

export interface FiltroColocaciones {
  page: number;
  pageSize: number;
  /** Vacío = sugeridas y confirmadas. */
  estado: EstadoColocacion | '';
  q: string;
}

export interface NuevaColocacion {
  egresado_id: string;
  empresa_id: string | null;
  empresa_nombre: string | null;
  cargo: string;
  fecha_inicio: string;
  salario: number | null;
  moneda: string | null;
}

/** Solo viajan los campos que cambiaron, más el motivo. */
export interface CambioColocacion {
  empresa_id?: string | null;
  empresa_nombre?: string | null;
  cargo?: string;
  fecha_inicio?: string;
  salario?: number | null;
  moneda?: string | null;
  motivo: string;
}

export interface EgresadoOpcion {
  id: string;
  nombre: string;
  correo: string | null;
  universidad: string | null;
}

export interface EmpresaOpcion {
  id: string;
  nombre: string;
}
