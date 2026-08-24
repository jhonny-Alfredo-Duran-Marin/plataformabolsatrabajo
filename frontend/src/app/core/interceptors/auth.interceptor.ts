/**
 * AuthInterceptor — HttpInterceptorFn moderno (Angular 18+).
 * - Inyecta automáticamente el header Authorization: Bearer <token> en peticiones a /api/.
 * - Captura errores 401 (sesión expirada) y 403 (acceso denegado) globalmente.
 */
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { TokenService } from '../services/token.service';
import { ToastService } from '../services/toast.service';
import { Router } from '@angular/router';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const tokens = inject(TokenService);
  const toast  = inject(ToastService);
  const router = inject(Router);

  // Solo enriquecer peticiones que van a la API propia
  const isApiCall = req.url.includes('/api/');
  const token = tokens.getAccessToken();

  // Clonar la petición inyectando el Bearer token si existe
  const authReq = (isApiCall && token)
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401) {
        // Sesión expirada o token inválido
        tokens.clearTokens();
        toast.warning('Tu sesión ha expirado. Inicia sesión nuevamente.');
        router.navigate(['/login']);
      } else if (err.status === 403) {
        toast.error('No tienes permisos para realizar esta acción.');
      } else if (err.status === 0) {
        toast.error('Sin conexión al servidor. Verifica tu red o que el backend esté activo.');
      }
      return throwError(() => err);
    })
  );
};
