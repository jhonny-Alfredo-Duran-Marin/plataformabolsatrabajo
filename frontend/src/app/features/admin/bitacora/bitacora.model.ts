export interface BitacoraLog {
  id: number;
  usuario_id: number | null;
  ip: string | null;
  modulo: string;
  accion: string;
  detalles: string | null;
  resultado: boolean;
  fecha: string;
}

export interface BitacoraFiltros {
  usuarioId: number | null;
  modulo: string;
  accion: string;
  fechaDesde: string;
  fechaHasta: string;
}
