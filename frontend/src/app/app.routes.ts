import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'auth/login',
    pathMatch: 'full',
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
    path: 'auth/registro-empresa',
    loadComponent: () =>
      import('./features/auth/registro-empresa/registro-empresa.component').then(
        (m) => m.RegistroEmpresaComponent,
      ),
  },
  {
    path: 'admin',
    loadComponent: () => import('./features/admin/layout/admin-layout').then((m) => m.AdminLayout),
    children: [
      {
        path: '',
        loadComponent: () => import('./features/admin/dashboard/dashboard').then((m) => m.Dashboard),
      },
      {
        path: 'roles',
        loadComponent: () =>
          import('./features/admin/gestion-roles/gestion-roles.component').then((m) => m.GestionRolesComponent),
      },
      {
        path: 'validacion-egresados',
        loadComponent: () =>
          import('./features/admin/validacion-egresados/validacion-egresados.component').then(
            (m) => m.ValidacionEgresadosComponent,
          ),
      },
      {
        path: 'empresas',
        loadComponent: () =>
          import('./features/admin/empresas-gestion/empresas-gestion.component').then(
            (m) => m.EmpresasGestionComponent,
          ),
      },
      {
        path: 'moderacion-vacantes',
        loadComponent: () =>
          import('./features/admin/moderacion-vacantes/moderacion-vacantes.component').then(
            (m) => m.ModeracionVacantesComponent,
          ),
      },
      {
        path: 'bitacora',
        loadComponent: () => import('./features/admin/bitacora/bitacora.component').then((m) => m.BitacoraComponent),
      },
    ],
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'perfil/visibilidad',
    loadComponent: () => import('./features/perfil/visibilidad/visibilidad.component').then((m) => m.VisibilidadComponent),
  },
  {
    path: 'perfil/profesional',
    loadComponent: () =>
      import('./features/perfil/profesional/profesional.component').then((m) => m.ProfesionalComponent),
  },
  {
    path: 'vacantes',
    redirectTo: 'vacantes/mis-vacantes',
    pathMatch: 'full',
  },
  {
    path: 'vacantes/crear',
    canActivate: [authGuard],
    data: { roles: ['EMPRESA'] },
    loadComponent: () =>
      import('./features/vacantes/crear-vacante/crear-vacante.component').then(
        (m) => m.CrearVacanteComponent,
      ),
  },
  {
    path: 'vacantes/mis-vacantes',
    canActivate: [authGuard],
    data: { roles: ['EMPRESA'] },
    loadComponent: () =>
      import('./features/vacantes/mis-vacantes/mis-vacantes.component').then(
        (m) => m.MisVacantesComponent,
      ),
  },
  {
    path: 'vacantes/:id',
    canActivate: [authGuard],
    data: { roles: ['EGRESADO', 'ESTUDIANTE', 'EMPRESA', 'ADMINISTRADOR'] },
    loadComponent: () =>
      import('./features/vacantes/vacante-detalle/vacante-detalle.component').then(
        (m) => m.VacanteDetalleComponent,
      ),
  },
];
