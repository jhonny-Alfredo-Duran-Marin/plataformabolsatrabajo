import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateChildFn, CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';

import { PermisosService } from '../services/permisos.service';
import { ToastService } from '../services/toast.service';

/** Pantallas del panel en el orden del menú: si falta el permiso se va a la primera permitida. */
export const PANTALLAS_ADMIN: { ruta: string; permiso: string }[] = [
  { ruta: '/admin', permiso: 'menu.dashboard' },
  { ruta: '/admin/validacion-egresados', permiso: 'menu.validacion' },
  { ruta: '/admin/empresas', permiso: 'menu.empresas' },
  { ruta: '/admin/moderacion-vacantes', permiso: 'menu.moderacion' },
  { ruta: '/admin/denuncias', permiso: 'menu.denuncias' },
  { ruta: '/admin/reportes', permiso: 'menu.reportes' },
  { ruta: '/admin/bitacora', permiso: 'menu.bitacora' },
  { ruta: '/admin/notificaciones', permiso: 'menu.alertas' },
  { ruta: '/admin/universidades', permiso: 'menu.universidades' },
  { ruta: '/admin/roles', permiso: 'menu.usuarios' },
  { ruta: '/admin/grupos', permiso: 'menu.grupos' },
];

/**
 * Pantallas solo del superadministrador del SaaS (admin sin universidad): copias de seguridad y
 * tareas automáticas. El backend igual las rechaza; esto evita una pantalla llena de errores.
 */
export const superadminGuard: CanActivateFn = () => {
  const esSuperadmin = localStorage.getItem('rol') === 'platform_admin' && !localStorage.getItem('institucion');
  if (esSuperadmin) return true;
  inject(ToastService).error('Esa sección es solo del superadministrador.');
  return inject(Router).parseUrl('/admin');
};

/**
 * Las rutas del panel declaran `data: { permiso: 'menu.x' }`. El backend ya rechaza los
 * datos sin permiso; esto evita mostrar una pantalla vacía o llena de errores.
 */
export const permisoGuard: CanActivateFn & CanActivateChildFn = (route: ActivatedRouteSnapshot) => {
  const permiso: string | undefined = route.data?.['permiso'];
  if (!permiso) return true;
  const permisos = inject(PermisosService);
  const toast = inject(ToastService);
  const router = inject(Router);

  return permisos.asegurar().pipe(
    map((cargados) => {
      // Sin respuesta del servidor se deja pasar: igual rechaza los datos sin permiso.
      if (!cargados || permisos.puede(permiso)) return true;
      toast.error('Tu grupo de usuarios no tiene acceso a esa sección.');
      const destino = PANTALLAS_ADMIN.find((p) => permisos.puede(p.permiso));
      return router.parseUrl(destino?.ruta ?? '/cuenta/contrasena');
    }),
  );
};
