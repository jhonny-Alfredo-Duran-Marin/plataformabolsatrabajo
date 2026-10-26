import { describe, expect, it } from 'vitest';

import {
  PreguntaEncuesta,
  ValoresEncuesta,
  armarRespuestas,
  esObligatoria,
  faltanRespuestas,
  preguntasVisibles,
  situacionElegida,
} from './encuestas.models';

const SITUACIONES = ['empleado', 'independiente', 'posgrado', 'buscando', 'sin_buscar'];

const PREGUNTAS: PreguntaEncuesta[] = [
  {
    id: 'q-situacion',
    codigo: 'situacion_laboral',
    texto: '¿Cuál es tu situación laboral actual?',
    tipo: 'single_choice',
    obligatoria: true,
    opciones: SITUACIONES.map((codigo) => ({ id: `o-${codigo}`, codigo, texto: codigo })),
  },
  { id: 'q-empresa', codigo: 'empresa', texto: 'Empresa', tipo: 'text', obligatoria: false, opciones: [] },
  { id: 'q-cargo', codigo: 'cargo', texto: 'Cargo', tipo: 'text', obligatoria: false, opciones: [] },
  { id: 'q-relacion', codigo: 'relacion_carrera', texto: 'Relación', tipo: 'scale', obligatoria: false, opciones: [] },
  { id: 'q-meses', codigo: 'meses_primer_empleo', texto: 'Meses', tipo: 'number', obligatoria: false, opciones: [] },
];

const vacio = (): ValoresEncuesta => ({ opciones: {}, textos: {}, numeros: {} });
const eligiendo = (situacion: string): ValoresEncuesta => ({
  ...vacio(),
  opciones: { 'q-situacion': `o-${situacion}` },
});

describe('encuesta de situación laboral (HU-30)', () => {
  it('sin elegir la situación solo se pregunta eso y los meses', () => {
    expect(situacionElegida(PREGUNTAS, vacio())).toBeNull();
    expect(preguntasVisibles(PREGUNTAS, vacio()).map((p) => p.codigo)).toEqual([
      'situacion_laboral',
      'meses_primer_empleo',
    ]);
  });

  it('quien trabaja ve además empresa, cargo y relación con la carrera', () => {
    for (const situacion of ['empleado', 'independiente']) {
      const valores = eligiendo(situacion);
      expect(situacionElegida(PREGUNTAS, valores)).toBe(situacion);
      expect(preguntasVisibles(PREGUNTAS, valores).map((p) => p.codigo)).toEqual([
        'situacion_laboral',
        'empresa',
        'cargo',
        'relacion_carrera',
        'meses_primer_empleo',
      ]);
    }
  });

  it('quien no trabaja no ve las preguntas de trabajo', () => {
    for (const situacion of ['posgrado', 'buscando', 'sin_buscar']) {
      expect(preguntasVisibles(PREGUNTAS, eligiendo(situacion)).map((p) => p.codigo)).not.toContain('empresa');
    }
  });

  it('empresa, cargo y relación son obligatorias solo si trabaja', () => {
    const empresa = PREGUNTAS[1];
    expect(esObligatoria(empresa, vacio(), PREGUNTAS)).toBe(false);
    expect(esObligatoria(empresa, eligiendo('buscando'), PREGUNTAS)).toBe(false);
    expect(esObligatoria(empresa, eligiendo('empleado'), PREGUNTAS)).toBe(true);
    expect(esObligatoria(PREGUNTAS[0], vacio(), PREGUNTAS)).toBe(true);
  });

  it('no se puede enviar hasta completar lo obligatorio', () => {
    expect(faltanRespuestas(PREGUNTAS, vacio())).toBe(true);
    // Quien está buscando empleo ya puede enviar con solo elegir su situación.
    expect(faltanRespuestas(PREGUNTAS, eligiendo('buscando'))).toBe(false);

    const trabaja = eligiendo('empleado');
    expect(faltanRespuestas(PREGUNTAS, trabaja)).toBe(true);
    trabaja.textos = { 'q-empresa': 'TecnoSur', 'q-cargo': 'Analista' };
    expect(faltanRespuestas(PREGUNTAS, trabaja)).toBe(true);
    trabaja.numeros = { 'q-relacion': 4 };
    expect(faltanRespuestas(PREGUNTAS, trabaja)).toBe(false);
  });

  it('un texto de solo espacios cuenta como sin responder', () => {
    const valores = eligiendo('empleado');
    valores.textos = { 'q-empresa': '   ', 'q-cargo': 'Analista' };
    valores.numeros = { 'q-relacion': 3 };
    expect(faltanRespuestas(PREGUNTAS, valores)).toBe(true);
  });

  it('arma solo las respuestas visibles y contestadas, con el texto limpio', () => {
    const valores: ValoresEncuesta = {
      opciones: { 'q-situacion': 'o-empleado' },
      textos: { 'q-empresa': '  TecnoSur ', 'q-cargo': 'Analista' },
      numeros: { 'q-relacion': 5, 'q-meses': 0 },
    };
    expect(armarRespuestas(PREGUNTAS, valores)).toEqual([
      { pregunta_id: 'q-situacion', opcion_id: 'o-empleado' },
      { pregunta_id: 'q-empresa', texto: 'TecnoSur' },
      { pregunta_id: 'q-cargo', texto: 'Analista' },
      { pregunta_id: 'q-relacion', numero: 5 },
      // Cero meses es una respuesta válida, no un campo vacío.
      { pregunta_id: 'q-meses', numero: 0 },
    ]);
  });

  it('si cambia a una situación sin trabajo, no manda lo que había escrito antes', () => {
    const valores: ValoresEncuesta = {
      opciones: { 'q-situacion': 'o-posgrado' },
      textos: { 'q-empresa': 'Quedó de antes', 'q-cargo': 'Quedó de antes' },
      numeros: { 'q-relacion': 5 },
    };
    expect(armarRespuestas(PREGUNTAS, valores)).toEqual([{ pregunta_id: 'q-situacion', opcion_id: 'o-posgrado' }]);
  });
});
