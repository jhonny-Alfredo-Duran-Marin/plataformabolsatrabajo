/**
 * AuthGuard — CanActivateFn moderno (Angular 18+).
 * Verifica autenticación y, opcionalmente, el rol requerido por la ruta.
 *
 * Uso en rutas:
 *   { path: 'dashboard/admin', canActivate: [authGuard], data: { roles: ['ADMIN'] }, ... }
 */
import { inject } from '@angular/core';
import { CanActivateFn, Router, ActivatedRouteSnapshot } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ToastService } from '../services/toast.service';

export const authGuard: CanActivateFn = (route: ActivatedRouteSnapshot) => {
  const auth  = inject(AuthService);
  const router = inject(Router);
  const toast = inject(ToastService);

  // 1. ¿Hay una sesión válida?
  if (!auth.isAuthenticated()) {
    // Guarda la URL intentada para redirigir después del login
    const returnUrl = route.url.map((s) => s.path).join('/');
    router.navigate(['/login'], { queryParams: returnUrl ? { returnUrl } : {} });
    return false;
  }

  // 2. ¿La ruta requiere roles específicos?
  const requiredRoles: string[] | undefined = route.data?.['roles'];
  if (requiredRoles && requiredRoles.length > 0) {
    const userRole = auth.getUserRole();
    if (!userRole || !requiredRoles.includes(userRole)) {
      toast.error('No tienes permisos para acceder a esta sección.');
      // Redirige al dashboard que le corresponde a su rol
      auth.redirectToDashboard();
      return false;
    }
  }

  return true;
};
