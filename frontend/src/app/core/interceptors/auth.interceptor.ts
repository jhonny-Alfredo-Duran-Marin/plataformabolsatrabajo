/**
 * AuthInterceptor — HttpInterceptorFn moderno (Angular 18+).
 * - Inyecta automáticamente el header Authorization: Bearer <token> en peticiones a /api/.
 * - Ante un 401 intenta renovar la sesión una vez con el refresh_token (silencioso, sin
 *   interrumpir al usuario) y reintenta la petición original; solo cierra sesión si la
 *   renovación también falla (HU-02: sesión se mantiene mientras haya actividad).
 * - Captura errores 403 (acceso denegado) globalmente.
 * - Los endpoints públicos de autenticación (login/registro) quedan fuera de este flujo,
 *   donde un 401 significa "credenciales incorrectas" y no "sesión expirada".
 */
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, shareReplay, switchMap, throwError } from 'rxjs';
import { AuthService } from '../../features/auth/auth.service';
import { ToastService } from '../services/toast.service';

const TOKEN_KEY = 'token';
const REFRESH_KEY = 'refresh_token';
const ROL_KEY = 'rol';
const CORREO_KEY = 'correo';

const _RUTAS_PUBLICAS = ['/auth/login', '/auth/registro', '/auth/refresh'];

let _refrescoEnCurso$: Observable<string> | null = null;

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const toast = inject(ToastService);
  const router = inject(Router);
  const auth = inject(AuthService);

  const isApiCall = req.url.includes('/api/');
  const esRutaPublica = _RUTAS_PUBLICAS.some((ruta) => req.url.includes(ruta));
  const token = localStorage.getItem(TOKEN_KEY);

  const authReq = isApiCall && token && !esRutaPublica
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  const cerrarSesionPorExpiracion = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(ROL_KEY);
    localStorage.removeItem(CORREO_KEY);
    toast.warning('Tu sesión ha expirado. Inicia sesión nuevamente.');
    router.navigate(['/auth/login']);
  };

  return next(authReq).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401 && !esRutaPublica && isApiCall && localStorage.getItem(REFRESH_KEY)) {
        if (!_refrescoEnCurso$) {
          _refrescoEnCurso$ = auth.refrescarToken().pipe(
            switchMap((respuesta) => [respuesta.access_token]),
            shareReplay(1),
          );
        }
        return _refrescoEnCurso$.pipe(
          switchMap((nuevoToken) => {
            _refrescoEnCurso$ = null;
            const reintento = req.clone({ setHeaders: { Authorization: `Bearer ${nuevoToken}` } });
            return next(reintento);
          }),
          catchError(() => {
            _refrescoEnCurso$ = null;
            cerrarSesionPorExpiracion();
            return throwError(() => err);
          }),
        );
      }

      if (err.status === 401 && !esRutaPublica) {
        cerrarSesionPorExpiracion();
      } else if (err.status === 403) {
        toast.error('No tienes permisos para realizar esta acción.');
      } else if (err.status === 0) {
        toast.error('Sin conexión al servidor. Verifica tu red o que el backend esté activo.');
      }
      return throwError(() => err);
    })
  );
};
