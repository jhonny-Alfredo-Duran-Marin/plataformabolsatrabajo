import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { passwordPendienteGuard } from './core/guards/password-pendiente.guard';
import { permisoGuard, superadminGuard } from './core/guards/permiso.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'vacantes',
    pathMatch: 'full',
  },
  {
    path: 'login',
    redirectTo: 'auth/login',
    pathMatch: 'full',
  },
  {
    path: 'registro',
    redirectTo: 'auth/registro',
    pathMatch: 'full',
  },
  {
    path: 'registro-empresa',
    redirectTo: 'auth/registro-empresa',
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
    path: 'registro-universidad',
    redirectTo: 'auth/registro-universidad',
    pathMatch: 'full',
  },
  {
    path: 'auth/registro-universidad',
    loadComponent: () =>
      import('./features/auth/registro-universidad/registro-universidad').then((m) => m.RegistroUniversidad),
  },
  {
    path: 'cuenta/contrasena',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/auth/cambiar-password/cambiar-password').then((m) => m.CambiarPassword),
  },
  {
    path: 'admin',
    // Sin sesión de staff no se muestra el panel (el backend igual rechaza los datos).
    canActivate: [authGuard, passwordPendienteGuard],
    data: { roles: ['platform_admin', 'moderator'] },
    canActivateChild: [passwordPendienteGuard, permisoGuard],
    loadComponent: () => import('./features/admin/layout/admin-layout').then((m) => m.AdminLayout),
    children: [
      {
        path: '',
        data: { permiso: 'menu.dashboard' },
        loadComponent: () => import('./features/admin/dashboard/dashboard').then((m) => m.Dashboard),
      },
      {
        path: 'universidades',
        data: { permiso: 'menu.universidades' },
        loadComponent: () =>
          import('./features/admin/universidades/universidades.component').then((m) => m.UniversidadesComponent),
      },
      {
        path: 'roles',
        data: { permiso: 'menu.usuarios' },
        loadComponent: () =>
          import('./features/admin/gestion-roles/gestion-roles.component').then((m) => m.GestionRolesComponent),
      },
      {
        path: 'grupos',
        data: { permiso: 'menu.grupos' },
        loadComponent: () =>
          import('./features/admin/grupos/grupos.component').then((m) => m.GruposComponent),
      },
      {
        path: 'validacion-egresados',
        data: { permiso: 'menu.validacion' },
        loadComponent: () =>
          import('./features/admin/validacion-egresados/validacion-egresados.component').then(
            (m) => m.ValidacionEgresadosComponent,
          ),
      },
      {
        path: 'empresas',
        data: { permiso: 'menu.empresas' },
        loadComponent: () =>
          import('./features/admin/empresas-gestion/empresas-gestion.component').then(
            (m) => m.EmpresasGestionComponent,
          ),
      },
      {
        path: 'moderacion-vacantes',
        data: { permiso: 'menu.moderacion' },
        loadComponent: () =>
          import('./features/admin/moderacion-vacantes/moderacion-vacantes.component').then(
            (m) => m.ModeracionVacantesComponent,
          ),
      },
      {
        path: 'denuncias',
        data: { permiso: 'menu.denuncias' },
        loadComponent: () =>
          import('./features/admin/denuncias/denuncias.component').then((m) => m.DenunciasComponent),
      },
      {
        path: 'encuestas',
        data: { permiso: 'menu.encuestas' },
        loadComponent: () =>
          import('./features/admin/encuestas/encuestas-admin.component').then((m) => m.EncuestasAdminComponent),
      },
      {
        path: 'colocaciones',
        data: { permiso: 'menu.colocaciones' },
        loadComponent: () =>
          import('./features/admin/colocaciones/colocaciones-admin.component').then((m) => m.ColocacionesAdminComponent),
      },
      {
        path: 'respaldos',
        canActivate: [superadminGuard],
        loadComponent: () => import('./features/admin/respaldos/respaldos.component').then((m) => m.RespaldosComponent),
      },
      {
        path: 'tareas',
        canActivate: [superadminGuard],
        loadComponent: () => import('./features/admin/tareas/tareas.component').then((m) => m.TareasComponent),
      },
      {
        path: 'reportes',
        data: { permiso: 'menu.reportes' },
        loadComponent: () =>
          import('./features/reportes/reporte-personalizado/reporte-personalizado.component').then(
            (m) => m.ReportePersonalizadoComponent,
          ),
      },
      {
        path: 'bitacora',
        data: { permiso: 'menu.bitacora' },
        loadComponent: () => import('./features/admin/bitacora/bitacora.component').then((m) => m.BitacoraComponent),
      },
      {
        path: 'notificaciones',
        data: { permiso: 'menu.alertas' },
        loadComponent: () =>
          import('./features/notificaciones/notificaciones-panel/notificaciones-panel.component').then(
            (m) => m.NotificacionesPanelComponent,
          ),
      },
    ],
  },
  {
    path: 'dashboard',
    canActivate: [authGuard, passwordPendienteGuard],
    loadComponent: () => import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'postulaciones',
    canActivate: [authGuard],
    data: { roles: ['candidate'] },
    loadComponent: () =>
      import('./features/postulaciones/mis-postulaciones/mis-postulaciones.component').then(
        (m) => m.MisPostulacionesComponent,
      ),
  },
  {
    path: 'reportes',
    canActivate: [authGuard],
    data: { roles: ['empresa'] },
    loadComponent: () =>
      import('./features/reportes/reporte-personalizado/reporte-personalizado.component').then(
        (m) => m.ReportePersonalizadoComponent,
      ),
  },
  {
    path: 'ayuda',
    loadComponent: () =>
      import('./features/ayuda/centro-ayuda/centro-ayuda.component').then((m) => m.CentroAyudaComponent),
  },
  {
    path: 'recomendaciones',
    canActivate: [authGuard],
    data: { roles: ['candidate'] },
    loadComponent: () =>
      import('./features/ia/recomendaciones/recomendaciones.component').then((m) => m.RecomendacionesComponent),
  },
  {
    path: 'encuestas',
    canActivate: [authGuard],
    data: { roles: ['candidate'] },
    loadComponent: () =>
      import('./features/encuestas/mis-encuestas/mis-encuestas.component').then((m) => m.MisEncuestasComponent),
  },
  {
    // A esta ruta apunta el aviso de la campanita cuando llega una encuesta.
    path: 'encuestas/:id',
    canActivate: [authGuard],
    data: { roles: ['candidate'] },
    loadComponent: () =>
      import('./features/encuestas/responder-encuesta/responder-encuesta.component').then(
        (m) => m.ResponderEncuestaComponent,
      ),
  },
  {
    path: 'seleccion',
    canActivate: [authGuard],
    data: { roles: ['empresa'] },
    loadComponent: () =>
      import('./features/seleccion/pipeline-seleccion/pipeline-seleccion.component').then(
        (m) => m.PipelineSeleccionComponent,
      ),
  },
  {
    path: 'perfil/visibilidad',
    canActivate: [authGuard],
    loadComponent: () => import('./features/perfil/visibilidad/visibilidad.component').then((m) => m.VisibilidadComponent),
  },
  {
    path: 'perfil/profesional',
    canActivate: [authGuard],
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
    path: 'empresa/sugerencias-ia',
    canActivate: [authGuard],
    data: { roles: ['EMPRESA'] },
    loadComponent: () =>
      import('./features/ia/sugerencias-candidatos/sugerencias-candidatos.component').then(
        (m) => m.SugerenciasCandidatosComponent,
      ),
  },
  {
    path: 'ia/sugerencias-candidatos',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/ia/sugerencias-candidatos/sugerencias-candidatos.component').then(
        (m) => m.SugerenciasCandidatosComponent,
      ),
  },
  {
    path: 'notificaciones',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/notificaciones/notificaciones-panel/notificaciones-panel.component').then(
        (m) => m.NotificacionesPanelComponent,
      ),
  },
  {
    path: 'vacantes/:id',
    loadComponent: () =>
      import('./features/vacantes/vacante-detalle/vacante-detalle.component').then(
        (m) => m.VacanteDetalleComponent,
      ),
  },
  {
    path: '**',
    redirectTo: 'auth/login',
  },
];
