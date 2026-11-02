export type TipoColumna = 'texto' | 'numero' | 'fecha' | 'estado' | 'booleano';
export type TipoFiltro = 'texto' | 'opciones' | 'fechas' | 'numeros';
export type FormatoReporte = 'excel' | 'pdf' | 'html';
export type Direccion = 'asc' | 'desc';

export interface ColumnaReporte {
  clave: string;
  etiqueta: string;
  tipo: TipoColumna;
  por_defecto: boolean;
}

export interface OpcionFiltro {
  valor: string;
  etiqueta: string;
}

export interface FiltroReporte {
  clave: string;
  etiqueta: string;
  tipo: TipoFiltro;
  opciones: OpcionFiltro[];
}

export interface OrdenReporte {
  columna: string;
  direccion: Direccion;
}

export interface FuenteReporte {
  clave: string;
  nombre: string;
  descripcion: string;
  columnas: ColumnaReporte[];
  filtros: FiltroReporte[];
  orden: OrdenReporte[];
}

export interface CatalogoReportes {
  fuentes: FuenteReporte[];
  correo_disponible: boolean;
  plan_permite: boolean;
  mensaje_plan: string | null;
  /** Se puede pedir el reporte con palabras (escrito o dictado): el servidor tiene la IA configurada. */
  ia_disponible: boolean;
}

/** Valor de un filtro según su tipo: texto, opciones elegidas, rango de fechas o de números. */
export type ValorFiltro =
  string | string[] | { desde: string; hasta: string } | { min: number | null; max: number | null };

export interface ConsultaReporte {
  fuente: string;
  columnas: string[];
  filtros: Record<string, ValorFiltro>;
  orden: OrdenReporte[];
  titulo: string | null;
}

export interface VistaPrevia {
  columnas: ColumnaReporte[];
  filas: unknown[][];
  total: number;
  pagina: number;
  tamanio: number;
  descripcion: string[];
}

/** Lo que armó la IA a partir de un pedido escrito o dictado; se revisa antes de exportar. */
export interface ReporteInterpretado {
  consulta: ConsultaReporte;
  explicacion: string;
  formato: FormatoReporte | null;
  motor: string;
}

export interface EnvioReporte {
  mensaje: string;
  destinatarios: string[];
}
