/**
 * TokenService — Responsabilidad única: persistencia y decodificación de JWT.
 * Desacoplado de AuthService para facilitar pruebas unitarias.
 */
import { Injectable } from '@angular/core';

const ACCESS_KEY  = 'token';
const REFRESH_KEY = 'refresh_token';
const ROL_KEY     = 'rol';

export interface JwtPayload {
  sub: string;      // ID del usuario
  rol: string;      // RolNombre: EGRESADO | ESTUDIANTE | EMPRESA | ADMINISTRADOR
  type: string;     // 'access' | 'refresh'
  iat: number;
  exp: number;
}

@Injectable({ providedIn: 'root' })
export class TokenService {

  // ── Escritura ────────────────────────────────────────────────────────────

  /** Guarda los tokens en localStorage (o sessionStorage si remember=false). */
  setTokens(accessToken: string, refreshToken: string, remember = true): void {
    const store = remember ? localStorage : sessionStorage;
    store.setItem(ACCESS_KEY,  accessToken);
    store.setItem(REFRESH_KEY, refreshToken);
    // Decodificar rol y cachearlo para acceso síncrono
    const payload = this.decodePayload(accessToken);
    if (payload?.rol) store.setItem(ROL_KEY, payload.rol);
  }

  // ── Lectura ──────────────────────────────────────────────────────────────

  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_KEY) ?? sessionStorage.getItem(ACCESS_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY) ?? sessionStorage.getItem(REFRESH_KEY);
  }

  getUserRole(): string | null {
    return localStorage.getItem(ROL_KEY) ?? sessionStorage.getItem(ROL_KEY);
  }

  // ── Limpieza ─────────────────────────────────────────────────────────────

  clearTokens(): void {
    [localStorage, sessionStorage].forEach((s) => {
      s.removeItem(ACCESS_KEY);
      s.removeItem(REFRESH_KEY);
      s.removeItem(ROL_KEY);
    });
  }

  // ── Decodificación JWT (sin librería externa) ─────────────────────────────

  decodePayload(token?: string | null): JwtPayload | null {
    const t = token ?? this.getAccessToken();
    if (!t) return null;
    try {
      const base64 = t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      return JSON.parse(atob(base64)) as JwtPayload;
    } catch {
      return null;
    }
  }

  /** Devuelve true si el access_token ha expirado o no existe. */
  isTokenExpired(): boolean {
    const payload = this.decodePayload();
    if (!payload) return true;
    // exp está en segundos epoch
    return Date.now() >= payload.exp * 1000;
  }

  hasValidSession(): boolean {
    return !!this.getAccessToken() && !this.isTokenExpired();
  }
}
