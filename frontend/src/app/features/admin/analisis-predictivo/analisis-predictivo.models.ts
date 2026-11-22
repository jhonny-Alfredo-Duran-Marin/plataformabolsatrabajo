/** HU-33: brecha entre las habilidades que piden las vacantes y las que declaran los egresados de una carrera. */

export interface CarreraOpcion {
  id: string;
  nombre: string;
}

export interface FiltrosBrecha {
  carreras: CarreraOpcion[];
  /** AAAA (año) o AAAA-MM (mes), del más reciente al más antiguo. */
  periodos: string[];
}

export interface BrechaHabilidad {
  habilidad: string;
  demanda_vacantes: number;
  demanda_pct: number;
  oferta_egresados: number;
  oferta_pct: number;
  /** demanda_pct - oferta_pct en puntos. Positiva: faltan egresados con la habilidad. */
  brecha: number;
}

export interface BrechaHabilidades {
  carrera_id: string;
  carrera_nombre: string;
  periodo: string | null;
  fecha_actualizacion: string;
  hay_suficientes_datos: boolean;
  /** Solo cuando faltan datos: qué falta y cuánto hay. */
  mensaje: string | null;
  minimo_requerido: number;
  total_vacantes: number;
  total_egresados: number;
  vacantes_sin_habilidades: number;
  egresados_sin_habilidades: number;
  total_habilidades: number;
  habilidades: BrechaHabilidad[];
  /** Lectura en texto de la IA; null si está apagada, falló o tardó demasiado. */
  resumen_ia: string | null;
}

const MESES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
];

/** «2026» → «Año 2026»; «2026-10» → «Octubre 2026». */
export function etiquetaPeriodo(periodo: string): string {
  const [anio, mes] = periodo.split('-');
  if (!mes) return `Año ${anio}`;
  const nombre = MESES[Number(mes) - 1] ?? mes;
  return `${nombre.charAt(0).toUpperCase()}${nombre.slice(1)} ${anio}`;
}
