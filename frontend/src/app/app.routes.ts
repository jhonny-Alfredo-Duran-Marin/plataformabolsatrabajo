import { Routes } from '@angular/router';

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
    path: 'postulaciones',
    loadComponent: () =>
      import('./features/postulaciones/mis-postulaciones/mis-postulaciones.component').then(
        (m) => m.MisPostulacionesComponent,
      ),
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
    path: 'seleccion',
    loadComponent: () =>
      import('./features/seleccion/pipeline-seleccion/pipeline-seleccion.component').then(
        (m) => m.PipelineSeleccionComponent,
      ),
  },
];
