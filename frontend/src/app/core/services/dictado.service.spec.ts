import { afterEach, describe, expect, it } from 'vitest';

import { DictadoService } from './dictado.service';

/** Imita el reconocimiento de voz del navegador. */
class ReconocimientoFalso {
  static ultimo: ReconocimientoFalso;
  lang = '';
  interimResults = false;
  continuous = true;
  maxAlternatives = 0;
  onresult: ((evento: { results: { transcript: string }[][] }) => void) | null = null;
  onerror: ((evento: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  iniciado = false;

  constructor() {
    ReconocimientoFalso.ultimo = this;
  }

  start(): void {
    this.iniciado = true;
  }

  stop(): void {
    this.onend?.();
  }

  decir(...partes: string[]): void {
    this.onresult?.({ results: partes.map((transcript) => [{ transcript }]) });
  }
}

const ventana = globalThis as unknown as Record<string, unknown>;

describe('DictadoService', () => {
  afterEach(() => {
    delete ventana['webkitSpeechRecognition'];
  });

  it('sin reconocimiento de voz en el navegador no ofrece dictar', async () => {
    const servicio = new DictadoService();
    expect(servicio.disponible).toBe(false);
    await expect(servicio.escuchar(() => undefined).resultado).rejects.toThrow('no permite dictar');
  });

  it('muestra el texto mientras se habla y entrega la frase al terminar', async () => {
    ventana['webkitSpeechRecognition'] = ReconocimientoFalso;
    const servicio = new DictadoService();
    const parciales: string[] = [];
    const escucha = servicio.escuchar((texto) => parciales.push(texto));
    const reconocimiento = ReconocimientoFalso.ultimo;

    expect(servicio.disponible).toBe(true);
    expect(reconocimiento.iniciado).toBe(true);
    expect(reconocimiento.lang).toBe('es-BO');
    expect(reconocimiento.interimResults).toBe(true);

    reconocimiento.decir('colocados de');
    reconocimiento.decir('colocados de', ' Sistemas ');
    reconocimiento.onend?.();

    await expect(escucha.resultado).resolves.toBe('colocados de Sistemas');
    expect(parciales).toEqual(['colocados de', 'colocados de Sistemas ']);
  });

  it('sin permiso de micrófono avisa qué hacer', async () => {
    ventana['webkitSpeechRecognition'] = ReconocimientoFalso;
    const escucha = new DictadoService().escuchar(() => undefined);
    ReconocimientoFalso.ultimo.onerror?.({ error: 'not-allowed' });
    ReconocimientoFalso.ultimo.onend?.();
    await expect(escucha.resultado).rejects.toThrow('Permití el uso del micrófono');
  });

  it('detenerlo a mitad entrega lo que ya se escuchó', async () => {
    ventana['webkitSpeechRecognition'] = ReconocimientoFalso;
    const escucha = new DictadoService().escuchar(() => undefined);
    ReconocimientoFalso.ultimo.decir('egresados validados');
    ReconocimientoFalso.ultimo.onerror?.({ error: 'aborted' });
    escucha.detener();
    await expect(escucha.resultado).resolves.toBe('egresados validados');
  });
});
