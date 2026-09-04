import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../../auth/auth.service';

interface ItemMenu {
  ruta: string;
  icono: string;
  etiqueta: string;
  exacta: boolean;
}

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './admin-layout.html',
  styleUrl: './admin-layout.scss',
})
export class AdminLayout {
  readonly auth = inject(AuthService);

  readonly correoInicial = (this.auth.correo() || 'A').charAt(0).toUpperCase();

  readonly itemsMenu: ItemMenu[] = [
    { ruta: '/admin', icono: '▦', etiqueta: 'Dashboard', exacta: true },
    { ruta: '/admin/roles', icono: '◉', etiqueta: 'Gestión de roles', exacta: false },
    { ruta: '/admin/validacion-egresados', icono: '✓', etiqueta: 'Validación de egresados', exacta: false },
    { ruta: '/admin/empresas', icono: '🏢', etiqueta: 'Gestión de empresas', exacta: false },
    { ruta: '/admin/bitacora', icono: '☰', etiqueta: 'Bitácora del sistema', exacta: false },
    { ruta: '/admin/seleccion', icono: '📊', etiqueta: 'Proceso de selección', exacta: false },
    { ruta: '/vacantes', icono: '💼', etiqueta: 'Bolsa de vacantes', exacta: false },
  ];

  cerrarSesion(): void {
    this.auth.cerrarSesion();
  }
}
