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
    if (!auth.estaAutenticado()) {
      // Ya se cerró (por ejemplo, la campana sondea y vuelve a fallar): sin avisos repetidos.
      void router.navigate(['/auth/login']);
      return;
    }
    toast.warning('Tu sesión ha expirado. Inicia sesión nuevamente.');
    // Limpia todo (señales, permisos, push, temporizador), no solo el almacenamiento, y va al login.
    auth.cerrarSesion();
  };

  const avisarError = (err: HttpErrorResponse) => {
    if (err.status === 403) {
      toast.error('No tienes permisos para realizar esta acción.');
    } else if (err.status === 0) {
      toast.error('Sin conexión al servidor. Verifica tu red o que el backend esté activo.');
    }
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
          // Solo un fallo de la renovación es «sesión expirada»: va antes del reintento.
          catchError(() => {
            _refrescoEnCurso$ = null;
            cerrarSesionPorExpiracion();
            return throwError(() => err);
          }),
          switchMap((nuevoToken) => {
            _refrescoEnCurso$ = null;
            const reintento = req.clone({ setHeaders: { Authorization: `Bearer ${nuevoToken}` } });
            // Un error del reintento (un 422, un 500) llega tal cual al componente.
            return next(reintento).pipe(
              catchError((errReintento: HttpErrorResponse) => {
                avisarError(errReintento);
                return throwError(() => errReintento);
              }),
            );
          }),
        );
      }

      if (err.status === 401 && !esRutaPublica) {
        cerrarSesionPorExpiracion();
      } else {
        avisarError(err);
      }
      return throwError(() => err);
    })
  );
};
