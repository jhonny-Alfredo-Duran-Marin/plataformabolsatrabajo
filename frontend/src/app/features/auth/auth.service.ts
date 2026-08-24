import { HttpClient } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

import { environment } from '../../../environments/environment';

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
}
