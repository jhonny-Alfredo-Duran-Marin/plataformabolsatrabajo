/**
 * AuthService — Orquestador principal de autenticación y estado reactivo del usuario.
 * Delega el manejo de tokens a TokenService para mantener responsabilidades separadas.
 */
import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, catchError, tap, throwError } from 'rxjs';
import { TokenService } from './token.service';
import { TimeoutService } from './timeout.service';
import { ToastService } from './toast.service';
import { environment } from '../../../environments/environment';

// ── Interfaces de API ─────────────────────────────────────────────────────────

export interface LoginRequest {
  correo: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  rol: 'EGRESADO' | 'ESTUDIANTE' | 'EMPRESA' | 'ADMINISTRADOR';
}

export type UserRole = 'EGRESADO' | 'ESTUDIANTE' | 'EMPRESA' | 'ADMINISTRADOR';

/** Mapa de roles a rutas de dashboard */
const ROLE_DASHBOARD: Record<UserRole, string> = {
  EGRESADO:      '/dashboard/egresado',
  ESTUDIANTE:    '/dashboard/egresado',
  EMPRESA:        '/dashboard/empresa',
  ADMINISTRADOR:  '/dashboard/admin',
};

const API = environment.apiUrl;

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http    = inject(HttpClient);
  private router  = inject(Router);
  private tokens  = inject(TokenService);
  private timeout = inject(TimeoutService);
  private toast   = inject(ToastService);

  // ── Estado Reactivo ───────────────────────────────────────────────────────

  private readonly _isAuth = signal<boolean>(this.tokens.hasValidSession());
  private readonly _role   = signal<UserRole | null>(this.tokens.getUserRole() as UserRole | null);

  readonly isAuthenticated = this._isAuth.asReadonly();
  readonly userRole        = this._role.asReadonly();
  readonly dashboardRoute  = computed(() => {
    const role = this._role();
    return role ? (ROLE_DASHBOARD[role] ?? '/dashboard') : '/login';
  });

  // Si ya hay una sesión válida al iniciar la app, arranca el timeout
  constructor() {
    if (this.tokens.hasValidSession()) {
      this.timeout.start(() => this.logout());
    }
  }

  // ── Autenticación ─────────────────────────────────────────────────────────

  login(credentials: LoginRequest, remember = true): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${API}/auth/login`, credentials).pipe(
      tap((resp) => {
        this.tokens.setTokens(resp.access_token, resp.refresh_token, remember);
        this._isAuth.set(true);
        this._role.set(resp.rol);
        this.timeout.start(() => this.logout());
      }),
      catchError((err: HttpErrorResponse) => throwError(() => this._parseError(err)))
    );
  }

  logout(): void {
    this.timeout.stop();
    this.tokens.clearTokens();
    this._isAuth.set(false);
    this._role.set(null);
    this.toast.info('Sesión cerrada correctamente.');
    this.router.navigate(['/login']);
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  getToken(): string | null  { return this.tokens.getAccessToken(); }
  getUserRole(): string | null { return this._role(); }

  /** Redirige al dashboard correspondiente al rol del usuario activo. */
  redirectToDashboard(): void {
    this.router.navigate([this.dashboardRoute()]);
  }

  // ── Manejo de Errores ─────────────────────────────────────────────────────

  private _parseError(err: HttpErrorResponse): string {
    if (err.status === 401) return 'Credenciales incorrectas. Verifica tus datos e intenta nuevamente.';
    if (err.status === 403) return 'Cuenta bloqueada temporalmente. Intenta en 15 minutos.';
    if (err.status === 0)   return 'No se pudo conectar al servidor. Verifica tu red.';
    const detail = err.error?.detail;
    if (typeof detail === 'string') return detail;
    return 'Error inesperado. Intenta nuevamente.';
  }
}
