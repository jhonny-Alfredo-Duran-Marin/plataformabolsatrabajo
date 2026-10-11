import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router, RouterStateSnapshot } from '@angular/router';
import { ToastService } from '../services/toast.service';

/**
 * AuthGuard — CanActivateFn moderno (Angular 18+).
 * Verifica sesión activa y roles requeridos directamente desde el almacenamiento local.
 */
export const authGuard: CanActivateFn = (route: ActivatedRouteSnapshot, state: RouterStateSnapshot) => {
  const router = inject(Router);
  const toast = inject(ToastService);

  // 1. ¿Hay un token de sesión activo?
  const token = localStorage.getItem('token');
  if (!token) {
    // La URL completa (con «/» inicial y parámetros): el login vuelve ahí al entrar.
    router.navigate(['/auth/login'], { queryParams: { returnUrl: state.url } });
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
