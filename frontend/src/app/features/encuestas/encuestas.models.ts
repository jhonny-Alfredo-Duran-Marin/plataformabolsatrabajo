/** HU-30: encuesta periódica de situación laboral de los egresados. */

export type AlcanceEncuesta = 'todas' | 'universidad' | 'carrera';
export type TipoPregunta = 'single_choice' | 'text' | 'number' | 'scale';

export interface Encuesta {
  id: string;
  titulo: string;
  descripcion: string | null;
  periodo: string;
  alcance: AlcanceEncuesta;
  carrera: string | null;
  enviada_el: string;
  vence_el: string | null;
  activa: boolean;
  /** Activa y sin vencer: la única que todavía recibe respuestas. */
  abierta: boolean;
  destinatarios: number;
  respondieron: number;
  porcentaje: number;
}

export interface EncuestasPagina {
  items: Encuesta[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface NuevaEncuesta {
  titulo: string;
  descripcion: string | null;
  periodo: string;
  carrera_id: string | null;
  /** Fecha (AAAA-MM-DD) hasta la que se puede responder. */
  vence_el: string | null;
}

export interface EncuestaCreada {
  encuesta: Encuesta;
  mensaje: string;
}

export interface SituacionLaboralCantidad {
  codigo: string;
  etiqueta: string;
  cantidad: number;
}

export interface AvanceEncuesta {
  encuesta: Encuesta;
  pendientes: number;
  situacion_laboral: SituacionLaboralCantidad[];
}

export interface MiEncuesta {
  id: string;
  titulo: string;
  descripcion: string | null;
  periodo: string;
  vence_el: string | null;
  respondida: boolean;
  respondida_el: string | null;
}

export interface OpcionEncuesta {
  id: string;
  codigo: string | null;
  texto: string;
}

export interface PreguntaEncuesta {
  id: string;
  codigo: string | null;
  texto: string;
  tipo: TipoPregunta;
  obligatoria: boolean;
  opciones: OpcionEncuesta[];
}

export interface FormularioEncuesta {
  id: string;
  titulo: string;
  descripcion: string | null;
  periodo: string;
  vence_el: string | null;
  preguntas: PreguntaEncuesta[];
}

export interface RespuestaPregunta {
  pregunta_id: string;
  opcion_id?: string | null;
  texto?: string | null;
  numero?: number | null;
}

export interface RespuestaCreada {
  mensaje: string;
  respondida_el: string;
}

/** Situaciones en las que el egresado trabaja y por eso declara empresa, cargo y relación con su carrera. */
export const SITUACIONES_CON_TRABAJO = ['empleado', 'independiente'];
/** Preguntas que solo se piden a quien trabaja. */
export const PREGUNTAS_DE_TRABAJO = ['empresa', 'cargo', 'relacion_carrera'];

export const ALCANCE_LEGIBLE: Record<AlcanceEncuesta, string> = {
  todas: 'Todos los egresados',
  universidad: 'Toda la universidad',
  carrera: 'Una carrera',
};

/** Lo que el egresado fue completando en el formulario, por id de pregunta. */
export interface ValoresEncuesta {
  opciones: Record<string, string>;
  textos: Record<string, string>;
  numeros: Record<string, number | null>;
}

/** Código de la situación laboral elegida (empleado, posgrado...), o null si todavía no eligió. */
export function situacionElegida(
  preguntas: PreguntaEncuesta[],
  valores: ValoresEncuesta,
): string | null {
  const pregunta = preguntas.find((p) => p.codigo === 'situacion_laboral');
  const opcionId = pregunta ? valores.opciones[pregunta.id] : undefined;
  return pregunta?.opciones.find((o) => o.id === opcionId)?.codigo ?? null;
}

/** Empresa, cargo y relación con la carrera solo se piden a quien trabaja. */
export function preguntasVisibles(
  preguntas: PreguntaEncuesta[],
  valores: ValoresEncuesta,
): PreguntaEncuesta[] {
  const trabaja = SITUACIONES_CON_TRABAJO.includes(situacionElegida(preguntas, valores) ?? '');
  return preguntas.filter((p) => trabaja || !PREGUNTAS_DE_TRABAJO.includes(p.codigo ?? ''));
}

export function estaRespondida(pregunta: PreguntaEncuesta, valores: ValoresEncuesta): boolean {
  switch (pregunta.tipo) {
    case 'single_choice':
      return !!valores.opciones[pregunta.id];
    case 'text':
      return (valores.textos[pregunta.id] ?? '').trim().length > 0;
    default:
      return valores.numeros[pregunta.id] != null;
  }
}

/** Obligatoria de por sí, o porque quien trabaja tiene que decir dónde, en qué y qué tan relacionado está. */
export function esObligatoria(
  pregunta: PreguntaEncuesta,
  valores: ValoresEncuesta,
  preguntas: PreguntaEncuesta[],
): boolean {
  if (pregunta.obligatoria) return true;
  const trabaja = SITUACIONES_CON_TRABAJO.includes(situacionElegida(preguntas, valores) ?? '');
  return trabaja && PREGUNTAS_DE_TRABAJO.includes(pregunta.codigo ?? '');
}

/** Faltan respuestas obligatorias: no se puede enviar todavía. */
export function faltanRespuestas(preguntas: PreguntaEncuesta[], valores: ValoresEncuesta): boolean {
  return preguntasVisibles(preguntas, valores).some(
    (p) => esObligatoria(p, valores, preguntas) && !estaRespondida(p, valores),
  );
}

/** Las respuestas a enviar: solo las preguntas visibles que el egresado contestó. */
export function armarRespuestas(
  preguntas: PreguntaEncuesta[],
  valores: ValoresEncuesta,
): RespuestaPregunta[] {
  const respuestas: RespuestaPregunta[] = [];
  for (const p of preguntasVisibles(preguntas, valores)) {
    if (!estaRespondida(p, valores)) continue;
    if (p.tipo === 'single_choice')
      respuestas.push({ pregunta_id: p.id, opcion_id: valores.opciones[p.id] });
    else if (p.tipo === 'text')
      respuestas.push({ pregunta_id: p.id, texto: valores.textos[p.id].trim() });
    else respuestas.push({ pregunta_id: p.id, numero: valores.numeros[p.id] });
  }
  return respuestas;
}
