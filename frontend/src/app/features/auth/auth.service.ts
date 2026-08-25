import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, tap, throwError } from 'rxjs';

import { environment } from '../../../environments/environment';
import { MessageResponse, RegistroEmpresaRequest } from '../../core/models/auth.models';

const TOKEN_KEY = 'token';
const ROL_KEY = 'rol';
const CORREO_KEY = 'correo';

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  rol: string;
  roles: string[];
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  readonly token = signal<string>(localStorage.getItem(TOKEN_KEY) ?? '');
  readonly rol = signal<string>(localStorage.getItem(ROL_KEY) ?? '');
  readonly correo = signal<string>(localStorage.getItem(CORREO_KEY) ?? '');

  constructor(
    private readonly http: HttpClient,
    private readonly router: Router,
  ) {}

  login(correoIngresado: string, password: string): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>(`${environment.apiUrl}/auth/login`, {
        correo: correoIngresado,
        password,
      })
      .pipe(
        tap((respuesta) => {
          localStorage.setItem(CORREO_KEY, correoIngresado);
          this.correo.set(correoIngresado);
          this.guardarSesion(respuesta);
        }),
      );
  }

  guardarSesion(respuesta: LoginResponse): void {
    localStorage.setItem(TOKEN_KEY, respuesta.access_token);
    localStorage.setItem(ROL_KEY, respuesta.rol);
    this.token.set(respuesta.access_token);
    this.rol.set(respuesta.rol);
  }

  cerrarSesion(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROL_KEY);
    localStorage.removeItem(CORREO_KEY);
    this.token.set('');
    this.rol.set('');
    this.correo.set('');
    void this.router.navigate(['/auth/login']);
  }

  estaAutenticado(): boolean {
    return this.token().length > 0;
  }

  /**
   * Envía la solicitud de registro de una empresa.
   * Queda en estado PENDIENTE de validación institucional.
   */
  registrarEmpresa(payload: RegistroEmpresaRequest): Observable<MessageResponse> {
    return this.http
      .post<MessageResponse>(`${environment.apiUrl}/auth/registro/empresa`, payload)
      .pipe(catchError(this.handleError));
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'Ocurrió un error inesperado al procesar la solicitud.';
    if (error.error) {
      if (typeof error.error.detail === 'string') {
        errorMessage = error.error.detail;
      } else if (Array.isArray(error.error.detail) && error.error.detail.length > 0) {
        errorMessage = error.error.detail.map((err: { msg: string }) => err.msg).join(', ');
      } else if (error.status === 0) {
        errorMessage = 'No se pudo conectar con el servidor de la API. Verifica tu conexión.';
      }
    }
    return throwError(() => new Error(errorMessage));
  }
}
