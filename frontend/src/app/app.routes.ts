import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'auth/login',
    pathMatch: 'full',
  },
  {
    path: 'login',
    redirectTo: 'auth/login',
    pathMatch: 'full',
  },
  {
<<<<<<< HEAD
    path: 'registro-empresa',
    redirectTo: 'auth/registro-empresa',
    pathMatch: 'full',
  },
  {
=======
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
    path: 'registro',
    redirectTo: 'auth/registro',
    pathMatch: 'full',
  },
  {
<<<<<<< HEAD
=======
    path: 'registro-empresa',
    redirectTo: 'auth/registro-empresa',
    pathMatch: 'full',
  },
  {
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
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
      {
        path: 'seleccion',
        loadComponent: () =>
          import('./features/seleccion/tablero-seleccion/tablero-seleccion.component').then(
            (m) => m.TableroSeleccionComponent,
          ),
      },
    ],
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
<<<<<<< HEAD
    path: 'seleccion',
    loadComponent: () =>
      import('./features/seleccion/tablero-seleccion/tablero-seleccion.component').then(
        (m) => m.TableroSeleccionComponent,
=======
    path: 'postulaciones',
    canActivate: [authGuard],
    data: { roles: ['candidate'] },
    loadComponent: () =>
      import('./features/postulaciones/mis-postulaciones/mis-postulaciones.component').then(
        (m) => m.MisPostulacionesComponent,
      ),
  },
  {
    path: 'seleccion',
    canActivate: [authGuard],
    data: { roles: ['empresa'] },
    loadComponent: () =>
      import('./features/seleccion/pipeline-seleccion/pipeline-seleccion.component').then(
        (m) => m.PipelineSeleccionComponent,
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
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
    path: 'vacantes',
    loadComponent: () =>
      import('./features/vacantes/busqueda-vacantes/busqueda-vacantes.component').then(
        (m) => m.BusquedaVacantesComponent,
      ),
  },
  {
    path: 'empleos',
    redirectTo: 'vacantes',
    pathMatch: 'full',
  },
  {
<<<<<<< HEAD
=======
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
  {
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
    path: '**',
    redirectTo: 'auth/login',
  },
];
