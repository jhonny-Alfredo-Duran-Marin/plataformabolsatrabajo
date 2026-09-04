import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../../auth/auth.service';

interface ItemMenu {
  ruta: string;
  etiqueta: string;
  tipoIcono: 'dashboard' | 'roles' | 'validacion' | 'empresas' | 'bitacora';
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
    { ruta: '/admin', tipoIcono: 'dashboard', etiqueta: 'Dashboard', exacta: true },
    { ruta: '/admin/roles', tipoIcono: 'roles', etiqueta: 'Gestión de roles', exacta: false },
    { ruta: '/admin/validacion-egresados', tipoIcono: 'validacion', etiqueta: 'Validación de egresados', exacta: false },
    { ruta: '/admin/empresas', tipoIcono: 'empresas', etiqueta: 'Gestión de empresas', exacta: false },
    { ruta: '/admin/bitacora', tipoIcono: 'bitacora', etiqueta: 'Bitácora del sistema', exacta: false },
  ];

  cerrarSesion(): void {
    this.auth.cerrarSesion();
  }
}
