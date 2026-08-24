import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'auth/login',
    pathMatch: 'full'
  },
  {
    path: 'auth/login',
    loadComponent: () => import('./features/auth/login/login').then((m) => m.Login),
  },
  {
    path: 'auth/registro',
    loadComponent: () => import('./features/auth/registro-egresado/registro-egresado').then((m) => m.RegistroEgresado),
  },
  {
    path: 'admin/bitacora',
    loadComponent: () => import('./features/admin/bitacora/bitacora.component').then((m) => m.BitacoraComponent),
  },
  {
    path: 'admin/validacion-egresados',
    loadComponent: () =>
      import('./features/admin/validacion-egresados/validacion-egresados.component').then(
        (m) => m.ValidacionEgresadosComponent,
      ),
  },
  {
    path: 'perfil/visibilidad',
    loadComponent: () => import('./features/perfil/visibilidad/visibilidad.component').then((m) => m.VisibilidadComponent),
  },
];
