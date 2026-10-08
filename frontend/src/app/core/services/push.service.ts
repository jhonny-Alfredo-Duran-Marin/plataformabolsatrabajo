import { HttpBackend, HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import type { Messaging } from 'firebase/messaging';
import { Subject, firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';

const FCM_TOKEN_KEY = 'fcm_token';

/**
 * - no-soportado: el navegador no admite push (o no es un contexto seguro).
 * - sin-permiso: todavía no se pidió, o se cerró la sesión con la que se registró.
 * - bloqueado: el usuario lo rechazó; solo se cambia desde los ajustes del sitio.
 * - activo: este navegador está registrado y recibe avisos.
 * - error: Firebase no devolvió un token (por ejemplo, sin conexión).
 */
export type EstadoPush = 'no-soportado' | 'sin-permiso' | 'bloqueado' | 'activo' | 'error';

export interface AvisoPush {
  titulo: string;
  cuerpo: string;
  link: string | null;
}

/**
 * Avisos push del navegador con Firebase Cloud Messaging (HU-21).
 * El SDK de Firebase se carga recién cuando hace falta, para no pesar en la carga inicial.
 */
@Injectable({ providedIn: 'root' })
export class PushService {
  private readonly http = inject(HttpClient);
  // Sin interceptores: al cerrar sesión, un token vencido no debe disparar "sesión expirada".
  private readonly httpDirecto = new HttpClient(inject(HttpBackend));
  private readonly base = `${environment.apiUrl}/notificaciones/fcm`;

  readonly estado = signal<EstadoPush>(this.estadoInicial());
  /** Avisos que llegan con la pestaña al frente: ahí Firebase no los muestra solo. */
  readonly avisos = new Subject<AvisoPush>();

  private messagingPromesa: Promise<Messaging | null> | null = null;
  private escuchando = false;

  private estadoInicial(): EstadoPush {
    if (typeof window === 'undefined' || !('Notification' in window) || !('serviceWorker' in navigator)) {
      return 'no-soportado';
    }
    if (Notification.permission === 'denied') return 'bloqueado';
    return Notification.permission === 'granted' && localStorage.getItem(FCM_TOKEN_KEY) ? 'activo' : 'sin-permiso';
  }

  private messaging(): Promise<Messaging | null> {
    this.messagingPromesa ??= (async () => {
      const { getMessaging, isSupported } = await import('firebase/messaging');
      if (!(await isSupported())) return null;
      const { getApps, initializeApp } = await import('firebase/app');
      return getMessaging(getApps()[0] ?? initializeApp(environment.firebase));
    })().catch(() => null);
    return this.messagingPromesa;
  }

  /** Con el permiso ya dado, registra (o renueva) el token de este navegador sin preguntar. */
  async sincronizar(): Promise<void> {
    if (this.estado() === 'no-soportado' || Notification.permission !== 'granted') return;
    await this.registrar();
  }

  /** Pide el permiso (tiene que venir de un clic del usuario) y registra este navegador. */
  async activar(): Promise<boolean> {
    if (this.estado() === 'no-soportado') return false;
    const permiso = await Notification.requestPermission();
    if (permiso !== 'granted') {
      this.estado.set(permiso === 'denied' ? 'bloqueado' : 'sin-permiso');
      return false;
    }
    return this.registrar();
  }

  private async registrar(): Promise<boolean> {
    try {
      const messaging = await this.messaging();
      if (!messaging) {
        this.estado.set('no-soportado');
        return false;
      }
      const { getToken, onMessage } = await import('firebase/messaging');
      const registro = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
      const token = await getToken(messaging, {
        vapidKey: environment.firebaseVapidKey,
        serviceWorkerRegistration: registro,
      });
      if (!token) {
        this.estado.set('error');
        return false;
      }
      await firstValueFrom(
        this.http.post(`${this.base}/registrar-token`, {
          fcm_token: token,
          device_type: 'web',
          device_name: this.nombreNavegador(),
        }),
      );
      localStorage.setItem(FCM_TOKEN_KEY, token);
      if (!this.escuchando) {
        this.escuchando = true;
        onMessage(messaging, (mensaje: any) =>
          this.avisos.next({
            titulo: mensaje.notification?.title ?? mensaje.data?.['title'] ?? 'EGRESA',
            cuerpo: mensaje.notification?.body ?? mensaje.data?.['body'] ?? '',
            link: mensaje.data?.['link'] ?? null,
          }),
        );
      }
      this.estado.set('activo');
      return true;
    } catch (err) {
      console.warn('[push] No se pudo activar en este navegador:', err);
      this.estado.set('error');
      return false;
    }
  }

  /** Al cerrar sesión: este navegador deja de recibir los avisos de esa cuenta. */
  desregistrar(accessToken: string): void {
    const token = localStorage.getItem(FCM_TOKEN_KEY);
    localStorage.removeItem(FCM_TOKEN_KEY);
    this.estado.set(this.estadoInicial());
    if (!token || !accessToken) return;
    this.httpDirecto
      .post(
        `${this.base}/eliminar-token`,
        { fcm_token: token },
        { headers: new HttpHeaders({ Authorization: `Bearer ${accessToken}` }) },
      )
      .subscribe({ error: () => undefined });
  }

  private nombreNavegador(): string {
    const ua = navigator.userAgent;
    const navegador = /Edg\//.test(ua) ? 'Edge' : /Firefox\//.test(ua) ? 'Firefox' : /Chrome\//.test(ua) ? 'Chrome' : /Safari\//.test(ua) ? 'Safari' : 'Navegador';
    const sistema = /Android/.test(ua) ? 'Android' : /iPhone|iPad/.test(ua) ? 'iOS' : /Windows/.test(ua) ? 'Windows' : /Mac OS/.test(ua) ? 'macOS' : /Linux/.test(ua) ? 'Linux' : '';
    return sistema ? `${navegador} en ${sistema}` : navegador;
  }
}
