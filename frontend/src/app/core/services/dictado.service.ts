import { Injectable } from '@angular/core';

/** Lo mínimo del reconocimiento de voz del navegador que se usa acá. */
interface Reconocimiento {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  onresult: ((evento: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((evento: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

type ConstructorReconocimiento = new () => Reconocimiento;

const MENSAJES_ERROR: Record<string, string> = {
  'not-allowed': 'Permití el uso del micrófono en el navegador para dictar.',
  'service-not-allowed': 'Permití el uso del micrófono en el navegador para dictar.',
  'no-speech': 'No te escuché. Probá de nuevo, cerca del micrófono.',
  'audio-capture': 'No se encontró un micrófono.',
  network: 'El dictado necesita conexión a internet.',
};

export interface Escucha {
  /** Termina de escuchar; la frase dicha hasta ahí igual se entrega. */
  detener(): void;
  /** La frase final, o un error con un mensaje para mostrar. */
  resultado: Promise<string>;
}

/**
 * Dictado por voz con el reconocimiento del propio navegador (Chrome, Edge y Safari). El
 * audio lo procesa el navegador; acá solo llega el texto, que la persona ve antes de usarlo.
 */
@Injectable({ providedIn: 'root' })
export class DictadoService {
  private readonly Reconocimiento: ConstructorReconocimiento | undefined = (() => {
    const ventana = globalThis as unknown as Record<string, ConstructorReconocimiento | undefined>;
    return ventana['SpeechRecognition'] ?? ventana['webkitSpeechRecognition'];
  })();

  readonly disponible = !!this.Reconocimiento;

  /** Escucha una frase; `parcial` recibe el texto mientras la persona habla. */
  escuchar(parcial: (texto: string) => void, idioma = 'es-BO'): Escucha {
    if (!this.Reconocimiento) {
      return { detener: () => {}, resultado: Promise.reject(new Error('Tu navegador no permite dictar.')) };
    }
    const reconocimiento = new this.Reconocimiento();
    reconocimiento.lang = idioma;
    reconocimiento.interimResults = true;
    reconocimiento.continuous = false;
    reconocimiento.maxAlternatives = 1;

    let texto = '';
    let error: string | null = null;
    const resultado = new Promise<string>((resolver, rechazar) => {
      reconocimiento.onresult = (evento) => {
        texto = Array.from(evento.results, (r) => r[0]?.transcript ?? '').join('');
        parcial(texto);
      };
      reconocimiento.onerror = (evento) => {
        // "aborted" es cuando la persona lo detiene: se usa lo que se escuchó.
        if (evento.error !== 'aborted') error = evento.error;
      };
      reconocimiento.onend = () => {
        if (error && !texto.trim()) {
          rechazar(new Error(MENSAJES_ERROR[error] ?? 'No se pudo usar el dictado. Escribí el pedido.'));
        } else {
          resolver(texto.trim());
        }
      };
    });
    reconocimiento.start();
    return { detener: () => reconocimiento.stop(), resultado };
  }
}
