import { Component, OnInit, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { PermisosService } from '../../../core/services/permisos.service';
import { AuthService } from '../../auth/auth.service';
import { NotificacionesCampanaComponent } from '../../../shared/components/notificaciones-campana/notificaciones-campana.component';

interface ItemMenu {
  ruta: string;
  etiqueta: string;
  tipoIcono:
    | 'dashboard'
    | 'universidades'
    | 'roles'
    | 'grupos'
    | 'validacion'
    | 'empresas'
    | 'moderacion'
    | 'denuncias'
    | 'encuestas'
    | 'colocaciones'
    | 'reportes'
    | 'bitacora'
    | 'respaldos'
    | 'tareas'
    | 'notificaciones';
  exacta: boolean;
  /** Componente del catálogo de permisos (requisito 2); lo deciden el rol y los grupos. */
  permiso?: string;
  /** Solo para el superadmin del SaaS (admin sin universidad). */
  soloSuperadmin?: boolean;
}

const ITEMS_MENU: ItemMenu[] = [
  { ruta: '/admin', tipoIcono: 'dashboard', etiqueta: 'Dashboard', exacta: true, permiso: 'menu.dashboard' },
  { ruta: '/admin/universidades', tipoIcono: 'universidades', etiqueta: 'Universidades', exacta: false, permiso: 'menu.universidades' },
  { ruta: '/admin/roles', tipoIcono: 'roles', etiqueta: 'Gestión de roles', exacta: false, permiso: 'menu.usuarios' },
  { ruta: '/admin/grupos', tipoIcono: 'grupos', etiqueta: 'Grupos y permisos', exacta: false, permiso: 'menu.grupos' },
  { ruta: '/admin/validacion-egresados', tipoIcono: 'validacion', etiqueta: 'Validación de egresados', exacta: false, permiso: 'menu.validacion' },
  { ruta: '/admin/empresas', tipoIcono: 'empresas', etiqueta: 'Gestión de empresas', exacta: false, permiso: 'menu.empresas' },
  { ruta: '/admin/moderacion-vacantes', tipoIcono: 'moderacion', etiqueta: 'Moderación de ofertas', exacta: false, permiso: 'menu.moderacion' },
  { ruta: '/admin/denuncias', tipoIcono: 'denuncias', etiqueta: 'Denuncias de ofertas', exacta: false, permiso: 'menu.denuncias' },
  { ruta: '/admin/encuestas', tipoIcono: 'encuestas', etiqueta: 'Encuestas laborales', exacta: false, permiso: 'menu.encuestas' },
  { ruta: '/admin/colocaciones', tipoIcono: 'colocaciones', etiqueta: 'Colocaciones', exacta: false, permiso: 'menu.colocaciones' },
  { ruta: '/admin/reportes', tipoIcono: 'reportes', etiqueta: 'Reportes personalizados', exacta: false, permiso: 'menu.reportes' },
  { ruta: '/admin/bitacora', tipoIcono: 'bitacora', etiqueta: 'Bitácora del sistema', exacta: false, permiso: 'menu.bitacora' },
  { ruta: '/admin/respaldos', tipoIcono: 'respaldos', etiqueta: 'Copias de seguridad', exacta: false, soloSuperadmin: true },
  { ruta: '/admin/tareas', tipoIcono: 'tareas', etiqueta: 'Tareas automáticas', exacta: false, soloSuperadmin: true },
  { ruta: '/admin/notificaciones', tipoIcono: 'notificaciones', etiqueta: 'Centro de Alertas', exacta: false, permiso: 'menu.alertas' },
];

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NotificacionesCampanaComponent],
  templateUrl: './admin-layout.html',
  styleUrl: './admin-layout.scss',
})
export class AdminLayout implements OnInit {
  readonly auth = inject(AuthService);
  private readonly permisos = inject(PermisosService);

  readonly correoInicial = (this.auth.correo() || 'A').charAt(0).toUpperCase();

  readonly itemsMenu = computed(() => {
    const superadmin = !this.auth.institucion() && this.auth.rol() === 'platform_admin';
    return ITEMS_MENU.filter(
      (item) => (!item.soloSuperadmin || superadmin) && (!item.permiso || this.permisos.puede(item.permiso)),
    );
  });

  ngOnInit(): void {
    // Un cambio en los grupos se ve al entrar al panel, sin cerrar sesión.
    this.permisos.refrescar().subscribe();
  }

  cerrarSesion(): void {
    this.auth.cerrarSesion();
  }
}
