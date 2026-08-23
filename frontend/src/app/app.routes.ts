import { Routes } from '@angular/router';

export const routes: Routes = [
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
];
