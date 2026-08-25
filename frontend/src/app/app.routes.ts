import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [

  // ── Raíz → Login ───────────────────────────────────────────────────────────
  { path: '', redirectTo: 'login', pathMatch: 'full' },

  // ── Públicas ────────────────────────────────────────────────────────────────
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'registro',
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
    // TODO: Reemplazar con RegistroComponent cuando esté implementado
  },

  // ── Dashboard Unificado (redirige por rol desde AuthService) ────────────────
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },

  // ── Sub-dashboards por Rol ─────────────────────────────────────────────────
  {
    path: 'dashboard/egresado',
    canActivate: [authGuard],
    data: { roles: ['EGRESADO', 'ESTUDIANTE'] },
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'dashboard/empresa',
    canActivate: [authGuard],
    data: { roles: ['EMPRESA'] },
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'dashboard/admin',
    canActivate: [authGuard],
    data: { roles: ['ADMINISTRADOR'] },
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },

  // ── Rutas protegidas ────────────────────────────────────────────────────────
  {
    path: 'perfil',
    canActivate: [authGuard],
    data: { roles: ['EGRESADO', 'ESTUDIANTE'] },
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
    // TODO: Reemplazar con PerfilComponent cuando esté implementado
  },
  {
    path: 'vacantes',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
    // TODO: Reemplazar con VacantesComponent cuando esté implementado
  },

  // ── Panel de Administración ─────────────────────────────────────────────────
  {
    path: 'admin/bitacora',
    canActivate: [authGuard],
    data: { roles: ['ADMINISTRADOR'] },
    loadComponent: () =>
      import('./features/admin/bitacora/bitacora.component').then((m) => m.BitacoraComponent),
  },
  {
    path: 'admin/validacion-egresados',
    canActivate: [authGuard],
    data: { roles: ['ADMINISTRADOR'] },
    loadComponent: () =>
      import('./features/admin/validacion-egresados/validacion-egresados.component').then(
        (m) => m.ValidacionEgresadosComponent,
      ),
  },

  // ── Comodín (404) → Login ───────────────────────────────────────────────────
  { path: '**', redirectTo: 'login' },
];
