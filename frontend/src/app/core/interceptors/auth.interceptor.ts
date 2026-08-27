/**
 * AuthInterceptor — HttpInterceptorFn moderno (Angular 18+).
 * - Inyecta automáticamente el header Authorization: Bearer <token> en peticiones a /api/.
 * - Captura errores 401 (sesión expirada) y 403 (acceso denegado) globalmente,
 *   salvo en los endpoints públicos de autenticación (login/registro), donde un 401
 *   significa "credenciales incorrectas" y no "sesión expirada".
 */
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { ToastService } from '../services/toast.service';
import { Router } from '@angular/router';

const TOKEN_KEY = 'token';
const ROL_KEY = 'rol';
const CORREO_KEY = 'correo';

const _RUTAS_PUBLICAS = ['/auth/login', '/auth/registro'];

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const toast = inject(ToastService);
  const router = inject(Router);

  const isApiCall = req.url.includes('/api/');
  const esRutaPublica = _RUTAS_PUBLICAS.some((ruta) => req.url.includes(ruta));
  const token = localStorage.getItem(TOKEN_KEY);

  const authReq = isApiCall && token && !esRutaPublica
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401 && !esRutaPublica) {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(ROL_KEY);
        localStorage.removeItem(CORREO_KEY);
        toast.warning('Tu sesión ha expirado. Inicia sesión nuevamente.');
        router.navigate(['/auth/login']);
      } else if (err.status === 403) {
        toast.error('No tienes permisos para realizar esta acción.');
      } else if (err.status === 0) {
        toast.error('Sin conexión al servidor. Verifica tu red o que el backend esté activo.');
      }
      return throwError(() => err);
    })
  );
};
