import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  ElementRef,
  ViewChild,
  effect,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../features/auth/auth.service';
import { AyudaService } from '../../../features/ayuda/ayuda.service';
import { IaService } from '../../../features/ia/ia.service';
import {
  ChatbotMensaje,
  ChatbotSesionResponse,
} from '../../../features/ia/recomendaciones.models';

type EstadoChatbot = 'inactivo' | 'cargando' | 'listo' | 'no_disponible' | 'error';

export interface SegmentoTexto {
  tipo: 'normal' | 'negrita' | 'codigo';
  texto: string;
}

/**
 * Chatbot de orientación (HU-28, módulo 5.1.13).
 *
 * Disponible para cualquier usuario autenticado. Permite hacer consultas en lenguaje
 * natural sobre el uso de EGRESA y, para egresados, consultar el estado real de sus
 * postulaciones sin exponer datos de otros usuarios.
 */
@Component({
  selector: 'app-chatbot-flotante',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    @if (auth.estaAutenticado() && !ia.chatbotAbierto() && !ayuda.abierto()) {
      <button
        type="button"
        class="boton-chatbot"
        (click)="abrir()"
        aria-expanded="false"
        aria-controls="panel-chatbot"
        title="Asistente de orientación (HU-28)"
      >
        <span class="boton-chatbot__icono" aria-hidden="true">🤖</span>
        <span class="boton-chatbot__texto">Asistente</span>
      </button>
    }

    @if (auth.estaAutenticado() && ia.chatbotAbierto()) {
      <div class="fondo" (click)="cerrar()" aria-hidden="true"></div>
      <aside
        id="panel-chatbot"
        class="panel"
        role="dialog"
        aria-modal="false"
        aria-labelledby="titulo-chatbot"
      >
        <header class="panel-cabecera">
          <div class="cabecera-info">
            <span class="avatar-bot" aria-hidden="true">🤖</span>
            <div>
              <h2 id="titulo-chatbot" class="panel-titulo">Asistente EGRESA</h2>
              <span
                class="estado-indicador"
                [class.estado-indicador--off]="estado() === 'no_disponible'"
              >
                {{
                  estado() === 'no_disponible'
                    ? 'No disponible temporalmente'
                    : 'Orientación y postulaciones'
                }}
              </span>
            </div>
          </div>
          <div class="cabecera-acciones">
            @if (estado() === 'listo' && mensajes().length > 0) {
              <button
                type="button"
                class="btn-icono"
                (click)="reiniciarSesion()"
                [disabled]="enviando()"
                title="Nueva conversación"
              >
                🔄
              </button>
            }
            <button
              type="button"
              class="btn-icono cerrar"
              (click)="cerrar()"
              aria-label="Cerrar asistente"
            >
              ✕
            </button>
          </div>
        </header>

        @switch (estado()) {
          @case ('cargando') {
            <div class="panel-estado">
              <div class="spinner"></div>
              <p>Conectando con el asistente de orientación…</p>
            </div>
          }
          @case ('no_disponible') {
            <div class="panel-estado panel-estado--aviso" role="status">
              <span class="estado-icono">🤖</span>
              <h3>Asistente no disponible temporalmente</h3>
              <p>{{ mensajeError() }}</p>
              <div class="estado-acciones">
                <button type="button" class="btn-primario" (click)="cargarSesion()">
                  Reintentar
                </button>
                <a routerLink="/ayuda" class="btn-secundario" (click)="cerrar()">
                  Ir al Centro de ayuda
                </a>
              </div>
            </div>
          }
          @case ('error') {
            <div class="panel-estado panel-estado--error" role="alert">
              <p>{{ mensajeError() }}</p>
              <button type="button" class="btn-primario" (click)="cargarSesion()">
                Reintentar
              </button>
            </div>
          }
          @case ('listo') {
            <div class="chat-cuerpo" #contenedorMensajes>
              <!-- Mensaje de bienvenida -->
              <div class="burbuja burbuja--bot">
                <div class="burbuja__cabecera">
                  <strong>Asistente EGRESA</strong>
                </div>
                <p class="burbuja__parrafo">{{ saludo() }}</p>
                <p class="burbuja__nota">
                  🔒 Tus consultas solo usan información de tu propia cuenta y quedan registradas para mejorar el servicio.
                </p>
              </div>

              <!-- Historial de mensajes de la sesión -->
              @for (m of mensajes(); track m.id) {
                <div
                  class="burbuja"
                  [class.burbuja--usuario]="m.role === 'user'"
                  [class.burbuja--bot]="m.role !== 'user'"
                  [class.burbuja--fuera]="m.en_alcance === false"
                >
                  <div class="burbuja__cabecera">
                    <strong>{{ m.role === 'user' ? 'Vos' : 'Asistente EGRESA' }}</strong>
                    <span class="burbuja__hora">{{ formatearHora(m.created_at) }}</span>
                  </div>

                  @for (linea of partirLineas(m.content); track $index) {
                    <p class="burbuja__parrafo">
                      @for (seg of formatearLinea(linea); track $index) {
                        @switch (seg.tipo) {
                          @case ('negrita') {
                            <strong>{{ seg.texto }}</strong>
                          }
                          @case ('codigo') {
                            <code>{{ seg.texto }}</code>
                          }
                          @default {
                            <span>{{ seg.texto }}</span>
                          }
                        }
                      }
                    </p>
                  }

                  <!-- Tarjetas de postulaciones reales (CP02) -->
                  @if (m.postulaciones && m.postulaciones.length > 0) {
                    <div class="postulaciones-lista">
                      @for (p of m.postulaciones; track p.application_id) {
                        <div class="postulacion-card">
                          <div class="postulacion-card__top">
                            <strong>{{ p.job_title }}</strong>
                            <span
                              class="badge-estado"
                              [attr.data-status]="p.current_status"
                            >
                              {{ p.status_label }}
                            </span>
                          </div>
                          <span class="postulacion-card__empresa">{{ p.company_name }}</span>
                          @if (p.etapa_actual) {
                            <span class="postulacion-card__etapa">
                              Etapa actual: <strong>{{ p.etapa_actual }}</strong>
                            </span>
                          }
                        </div>
                      }
                    </div>
                  }

                  <!-- Enlaces rápidos sugeridos en la respuesta -->
                  @if (m.enlaces_utiles && m.enlaces_utiles.length > 0) {
                    <div class="enlaces-utiles">
                      @for (enlace of m.enlaces_utiles; track enlace.ruta) {
                        <button
                          type="button"
                          class="enlace-chip"
                          (click)="irARuta(enlace.ruta)"
                        >
                          {{ enlace.texto }} →
                        </button>
                      }
                    </div>
                  }
                </div>
              }

              @if (enviando()) {
                <div class="burbuja burbuja--bot burbuja--escribiendo">
                  <span>Consultando…</span>
                </div>
              }

              <!-- Sugerencias rápidas -->
              @if (sugerencias().length > 0 && !enviando()) {
                <div class="sugerencias">
                  <span class="sugerencias__titulo">Preguntas frecuentes:</span>
                  <div class="sugerencias__chips">
                    @for (s of sugerencias(); track s) {
                      <button
                        type="button"
                        class="chip-sugerencia"
                        (click)="enviarPregunta(s)"
                      >
                        {{ s }}
                      </button>
                    }
                  </div>
                </div>
              }
            </div>

            <form class="chat-entrada" (ngSubmit)="enviarFormulario()">
              <input
                type="text"
                name="consulta"
                [(ngModel)]="textoEntrada"
                [disabled]="enviando()"
                maxlength="1000"
                placeholder="Preguntá sobre la plataforma o tus postulaciones…"
                aria-label="Escribir consulta al asistente"
                autocomplete="off"
              />
              <button
                type="submit"
                class="btn-enviar"
                [disabled]="enviando() || !textoEntrada.trim()"
              >
                Enviar
              </button>
            </form>
          }
        }
      </aside>
    }
  `,
  styles: [
    `
      :host {
        font-family:
          'Inter',
          system-ui,
          -apple-system,
          BlinkMacSystemFont,
          'Segoe UI',
          Roboto,
          sans-serif;
      }

      .boton-chatbot {
        position: fixed;
        right: 4.8rem;
        bottom: 1.25rem;
        z-index: 900;
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        height: 3rem;
        padding: 0 1rem;
        border: none;
        border-radius: 9999px;
        background: linear-gradient(135deg, #2563eb, #7c3aed);
        color: #ffffff;
        font-size: 0.88rem;
        font-weight: 700;
        box-shadow: 0 10px 24px -8px rgba(79, 70, 229, 0.65);
        cursor: pointer;
        transition:
          transform 0.15s ease,
          box-shadow 0.15s ease;
      }

      .boton-chatbot:hover {
        transform: translateY(-2px);
        box-shadow: 0 14px 28px -8px rgba(79, 70, 229, 0.8);
      }

      .boton-chatbot__icono {
        font-size: 1.15rem;
      }

      .fondo {
        position: fixed;
        inset: 0;
        z-index: 901;
        background: rgba(15, 23, 42, 0.22);
      }

      .panel {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        z-index: 902;
        display: flex;
        flex-direction: column;
        width: min(430px, 100vw);
        background: #f8fafc;
        border-left: 1px solid #e2e8f0;
        box-shadow: -16px 0 40px -18px rgba(15, 23, 42, 0.35);
        animation: deslizar 0.18s ease-out;
        color: #1e293b;
      }

      @keyframes deslizar {
        from {
          transform: translateX(24px);
          opacity: 0;
        }
      }

      .panel-cabecera {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.95rem 1.1rem;
        background: linear-gradient(135deg, #1e3a8a, #4f46e5);
        color: #ffffff;
      }

      .cabecera-info {
        display: flex;
        align-items: center;
        gap: 0.7rem;
      }

      .avatar-bot {
        display: grid;
        place-items: center;
        width: 2.3rem;
        height: 2.3rem;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.18);
        font-size: 1.2rem;
      }

      .panel-titulo {
        margin: 0;
        font-size: 1rem;
        font-weight: 800;
      }

      .estado-indicador {
        display: inline-block;
        font-size: 0.74rem;
        color: rgba(255, 255, 255, 0.85);
      }

      .estado-indicador--off {
        color: #fde68a;
        font-weight: 600;
      }

      .cabecera-acciones {
        display: flex;
        align-items: center;
        gap: 0.35rem;
      }

      .btn-icono {
        display: grid;
        place-items: center;
        width: 2rem;
        height: 2rem;
        border: none;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.14);
        color: #ffffff;
        font-size: 0.95rem;
        cursor: pointer;
      }

      .btn-icono:hover {
        background: rgba(255, 255, 255, 0.25);
      }

      .panel-estado {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem 1.5rem;
        text-align: center;
        gap: 0.75rem;
      }

      .panel-estado h3 {
        margin: 0.2rem 0 0;
        font-size: 1.1rem;
        color: #0f172a;
      }

      .panel-estado p {
        margin: 0;
        font-size: 0.9rem;
        line-height: 1.5;
        color: #475569;
      }

      .estado-icono {
        font-size: 2.6rem;
      }

      .estado-acciones {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
        justify-content: center;
        margin-top: 0.5rem;
      }

      .spinner {
        width: 2.2rem;
        height: 2.2rem;
        border: 3px solid #cbd5e1;
        border-top-color: #4f46e5;
        border-radius: 50%;
        animation: girar 0.75s linear infinite;
      }

      @keyframes girar {
        to {
          transform: rotate(360deg);
        }
      }

      .chat-cuerpo {
        flex: 1;
        overflow-y: auto;
        padding: 1rem;
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
      }

      .burbuja {
        max-width: 90%;
        padding: 0.8rem 0.95rem;
        border-radius: 14px;
        font-size: 0.88rem;
        line-height: 1.48;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
      }

      .burbuja--bot {
        align-self: flex-start;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-top-left-radius: 4px;
        color: #1e293b;
      }

      .burbuja--fuera {
        border-color: #cbd5e1;
        background: #f8fafc;
      }

      .burbuja--usuario {
        align-self: flex-end;
        background: linear-gradient(135deg, #2563eb, #4f46e5);
        color: #ffffff;
        border-top-right-radius: 4px;
      }

      .burbuja--escribiendo {
        color: #64748b;
        font-style: italic;
      }

      .burbuja__cabecera {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.3rem;
        font-size: 0.74rem;
        opacity: 0.82;
      }

      .burbuja__parrafo {
        margin: 0.25rem 0;
        word-break: break-word;
      }

      .burbuja__parrafo code {
        padding: 0.1rem 0.35rem;
        border-radius: 4px;
        background: #f1f5f9;
        color: #334155;
        font-size: 0.8rem;
      }

      .burbuja--usuario .burbuja__parrafo code {
        background: rgba(255, 255, 255, 0.2);
        color: #ffffff;
      }

      .burbuja__nota {
        margin: 0.5rem 0 0;
        padding-top: 0.45rem;
        border-top: 1px dashed #e2e8f0;
        font-size: 0.76rem;
        color: #64748b;
      }

      .postulaciones-lista {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        margin-top: 0.65rem;
      }

      .postulacion-card {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
        padding: 0.6rem 0.75rem;
        border-radius: 10px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
      }

      .postulacion-card__top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 0.5rem;
        font-size: 0.84rem;
      }

      .postulacion-card__empresa {
        font-size: 0.78rem;
        color: #475569;
      }

      .postulacion-card__etapa {
        font-size: 0.75rem;
        color: #334155;
      }

      .badge-estado {
        padding: 0.15rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.7rem;
        font-weight: 700;
        background: #e0e7ff;
        color: #1e40af;
        white-space: nowrap;
      }

      .badge-estado[data-status='hired'],
      .badge-estado[data-status='offer'] {
        background: #dcfce7;
        color: #15803d;
      }

      .badge-estado[data-status='rejected'],
      .badge-estado[data-status='withdrawn'] {
        background: #fee2e2;
        color: #b91c1c;
      }

      .enlaces-utiles {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-top: 0.6rem;
      }

      .enlace-chip {
        padding: 0.3rem 0.65rem;
        border-radius: 9999px;
        border: 1px solid #c7d2fe;
        background: #eef2ff;
        color: #3730a3;
        font-size: 0.76rem;
        font-weight: 600;
        cursor: pointer;
      }

      .enlace-chip:hover {
        background: #e0e7ff;
      }

      .sugerencias {
        margin-top: 0.25rem;
      }

      .sugerencias__titulo {
        display: block;
        margin-bottom: 0.4rem;
        font-size: 0.75rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }

      .sugerencias__chips {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
      }

      .chip-sugerencia {
        padding: 0.4rem 0.7rem;
        border: 1px solid #cbd5e1;
        border-radius: 9999px;
        background: #ffffff;
        color: #1e293b;
        font-size: 0.78rem;
        text-align: left;
        cursor: pointer;
        transition:
          border-color 0.15s,
          background 0.15s;
      }

      .chip-sugerencia:hover {
        border-color: #4f46e5;
        background: #eef2ff;
        color: #312e81;
      }

      .chat-entrada {
        display: flex;
        gap: 0.5rem;
        padding: 0.8rem 0.95rem;
        background: #ffffff;
        border-top: 1px solid #e2e8f0;
      }

      .chat-entrada input {
        flex: 1;
        padding: 0.6rem 0.8rem;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        font-size: 0.88rem;
        font-family: inherit;
      }

      .chat-entrada input:focus {
        outline: none;
        border-color: #4f46e5;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12);
      }

      .btn-enviar,
      .btn-primario {
        padding: 0.6rem 1rem;
        border: none;
        border-radius: 10px;
        background: linear-gradient(135deg, #2563eb, #4f46e5);
        color: #ffffff;
        font-size: 0.85rem;
        font-weight: 700;
        cursor: pointer;
      }

      .btn-enviar:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .btn-secundario {
        padding: 0.6rem 1rem;
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        background: #ffffff;
        color: #1e293b;
        font-size: 0.85rem;
        font-weight: 600;
        text-decoration: none;
      }
    `,
  ],
})
export class ChatbotFlotanteComponent {
  readonly auth = inject(AuthService);
  readonly ia = inject(IaService);
  readonly ayuda = inject(AyudaService);
  private readonly router = inject(Router);

  @ViewChild('contenedorMensajes')
  private contenedorMensajes?: ElementRef<HTMLDivElement>;

  readonly estado = signal<EstadoChatbot>('inactivo');
  readonly enviando = signal(false);
  readonly mensajeError = signal('');
  readonly sessionId = signal<string | null>(null);
  readonly saludo = signal('');
  readonly sugerencias = signal<string[]>([]);
  readonly mensajes = signal<ChatbotMensaje[]>([]);

  textoEntrada = '';
  private ultimoCorreoCargado = '';

  constructor() {
    effect(() => {
      const abierto = this.ia.chatbotAbierto();
      const autenticado = this.auth.estaAutenticado();
      const correo = this.auth.correo();

      if (!autenticado) {
        this.limpiarEstado();
        return;
      }

      if (abierto && (this.estado() === 'inactivo' || this.ultimoCorreoCargado !== correo)) {
        this.ultimoCorreoCargado = correo;
        this.cargarSesion();
      }
    });
  }

  abrir(): void {
    this.ayuda.cerrar();
    this.ia.abrirChatbot();
  }

  cerrar(): void {
    this.ia.cerrarChatbot();
  }

  cargarSesion(): void {
    this.estado.set('cargando');
    this.mensajeError.set('');
    this.ia.abrirSesionChatbot(this.sessionId()).subscribe({
      next: (sesion) => this.aplicarSesion(sesion),
      error: (err: HttpErrorResponse) => this.manejarError(err),
    });
  }

  reiniciarSesion(): void {
    if (this.enviando()) return;
    this.estado.set('cargando');
    this.ia.nuevaSesionChatbot().subscribe({
      next: (sesion) => this.aplicarSesion(sesion),
      error: (err: HttpErrorResponse) => this.manejarError(err),
    });
  }

  enviarFormulario(): void {
    const texto = this.textoEntrada.trim();
    if (!texto || this.enviando()) return;
    this.textoEntrada = '';
    this.enviarPregunta(texto);
  }

  enviarPregunta(pregunta: string): void {
    if (this.enviando()) return;
    this.enviando.set(true);

    this.ia.consultarChatbot(pregunta, this.sessionId()).subscribe({
      next: (res) => {
        this.sessionId.set(res.session_id);
        const msgUsuario: ChatbotMensaje = res.mensaje_usuario;
        const msgBot: ChatbotMensaje = {
          ...res.respuesta,
          postulaciones: res.postulaciones,
          enlaces_utiles: res.enlaces_utiles,
          en_alcance: res.en_alcance,
        };
        this.mensajes.update((actual) => [...actual, msgUsuario, msgBot]);
        this.sugerencias.set(res.sugerencias);
        this.enviando.set(false);
        this.desplazarAbajo();
      },
      error: (err: HttpErrorResponse) => {
        this.enviando.set(false);
        this.manejarError(err);
      },
    });
  }

  irARuta(ruta: string): void {
    this.cerrar();
    void this.router.navigateByUrl(ruta);
  }

  formatearHora(iso: string): string {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleTimeString('es-BO', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  }

  partirLineas(contenido: string): string[] {
    return (contenido || '').split('\n').filter((l) => l.trim().length > 0);
  }

  formatearLinea(linea: string): SegmentoTexto[] {
    const segmentos: SegmentoTexto[] = [];
    const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
    let ultimoIndice = 0;
    let coincidencia: RegExpExecArray | null;

    while ((coincidencia = regex.exec(linea)) !== null) {
      if (coincidencia.index > ultimoIndice) {
        segmentos.push({
          tipo: 'normal',
          texto: linea.slice(ultimoIndice, coincidencia.index),
        });
      }
      const token = coincidencia[0];
      if (token.startsWith('**') && token.endsWith('**')) {
        segmentos.push({ tipo: 'negrita', texto: token.slice(2, -2) });
      } else if (token.startsWith('`') && token.endsWith('`')) {
        segmentos.push({ tipo: 'codigo', texto: token.slice(1, -1) });
      }
      ultimoIndice = regex.lastIndex;
    }

    if (ultimoIndice < linea.length) {
      segmentos.push({ tipo: 'normal', texto: linea.slice(ultimoIndice) });
    }
    return segmentos;
  }

  private aplicarSesion(sesion: ChatbotSesionResponse): void {
    this.sessionId.set(sesion.session_id);
    this.saludo.set(sesion.saludo);
    this.sugerencias.set(sesion.sugerencias);
    this.mensajes.set(sesion.mensajes);
    this.estado.set('listo');
    this.desplazarAbajo();
  }

  private manejarError(err: HttpErrorResponse): void {
    const detalle = typeof err.error?.detail === 'string' ? err.error.detail : '';
    if (err.status === 503 || err.status === 0) {
      this.estado.set('no_disponible');
      this.mensajeError.set(
        detalle ||
          'El asistente de orientación no está disponible temporalmente. Podés consultar el Centro de ayuda o intentar más tarde.',
      );
    } else {
      this.estado.set('error');
      this.mensajeError.set(detalle || 'No se pudo comunicar con el asistente.');
    }
  }

  private limpiarEstado(): void {
    this.estado.set('inactivo');
    this.sessionId.set(null);
    this.mensajes.set([]);
    this.sugerencias.set([]);
    this.ultimoCorreoCargado = '';
    this.ia.cerrarChatbot();
  }

  private desplazarAbajo(): void {
    setTimeout(() => {
      const el = this.contenedorMensajes?.nativeElement;
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    }, 50);
  }
}
