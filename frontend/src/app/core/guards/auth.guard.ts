import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router } from '@angular/router';
import { ToastService } from '../services/toast.service';

/**
 * AuthGuard — CanActivateFn moderno (Angular 18+).
 * Verifica sesión activa y roles requeridos directamente desde el almacenamiento local.
 */
export const authGuard: CanActivateFn = (route: ActivatedRouteSnapshot) => {
  const router = inject(Router);
  const toast = inject(ToastService);

  // 1. ¿Hay un token de sesión activo?
  const token = localStorage.getItem('token');
  if (!token) {
    const returnUrl = route.url.map((s) => s.path).join('/');
    router.navigate(['/auth/login'], { queryParams: returnUrl ? { returnUrl } : {} });
    return false;
  }

  // 2. ¿La ruta requiere roles específicos?
  const requiredRoles: string[] | undefined = route.data?.['roles'];
  if (requiredRoles && requiredRoles.length > 0) {
    const userRole = (localStorage.getItem('rol') || '').toUpperCase();
    const allowed = requiredRoles.map((r) => r.toUpperCase());
    if (!userRole || !allowed.includes(userRole)) {
      toast.error('No tienes permisos para acceder a esta sección.');
      router.navigate(['/dashboard']);
      return false;
    }
  }

  return true;
};
