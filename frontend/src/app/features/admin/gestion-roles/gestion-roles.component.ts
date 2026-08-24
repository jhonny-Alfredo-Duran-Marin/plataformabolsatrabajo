import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../auth/auth.service';
import {
  ETIQUETAS_ROL,
  Rol,
  UsuarioAdmin,
} from './gestion-roles.model';
import { GestionRolesService } from './gestion-roles.service';

@Component({
  selector: 'app-gestion-roles',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './gestion-roles.html',
  styleUrl: './gestion-roles.scss',
})
export class GestionRolesComponent {
  private readonly service = inject(GestionRolesService);
  private readonly auth = inject(AuthService);

  readonly etiquetasRol = ETIQUETAS_ROL;
  readonly rolesAsignables = signal<Rol[]>([]);
  readonly usuarios = signal<UsuarioAdmin[]>([]);
  readonly seleccionados = signal<Record<string, string>>({});
  readonly busqueda = signal('');
  readonly cargando = signal(false);
  readonly guardandoId = signal<string | null>(null);
  readonly error = signal('');
  readonly mensaje = signal('');

  readonly filtrados = computed(() => {
    const texto = this.busqueda().trim().toLowerCase();
    if (!texto) return this.usuarios();
    return this.usuarios().filter(
      (u) =>
        u.correo.toLowerCase().includes(texto) ||
        this.rolPrincipal(u).toLowerCase().includes(texto),
    );
  });

  rolPrincipal(usuario: UsuarioAdmin): string {
    if (usuario.roles.length > 0) return ETIQUETAS_ROL[usuario.roles[0]] ?? usuario.roles[0];
    if (usuario.es_miembro_empresa) return 'Empresa';
    return 'Sin rol';
  }

  rolActual(usuario: UsuarioAdmin): string {
    const sel = this.seleccionados()[usuario.id];
    if (sel) return sel;
    if (usuario.roles.length > 0) return usuario.roles[0];
    return '';
  }

  cambioPendiente(usuario: UsuarioAdmin): boolean {
    const actual = usuario.roles[0] ?? '';
    return this.rolActual(usuario) !== actual;
  }

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    const token = this.auth.token();
    if (!token) {
      this.error.set('Inicia sesión como administrador para gestionar los roles.');
      return;
    }

    this.cargando.set(true);
    this.error.set('');
    this.service.listarUsuarios(token).subscribe({
      next: (usuarios) => {
        this.usuarios.set(usuarios);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar la lista de usuarios. Verifica que seas administrador.');
        this.cargando.set(false);
      },
    });

    this.service.listarRoles(token).subscribe({
      next: (roles) => this.rolesAsignables.set(roles),
      error: () => {
        /* el listado de usuarios no depende de este catálogo */
      },
    });
  }

  seleccionarRol(usuarioId: string, rol: string): void {
    this.seleccionados.update((sels) => ({ ...sels, [usuarioId]: rol }));
  }

  guardar(usuario: UsuarioAdmin): void {
    const rol = this.rolActual(usuario);
    if (!rol) {
      this.error.set('Selecciona un rol antes de guardar.');
      return;
    }

    this.guardandoId.set(usuario.id);
    this.error.set('');
    this.mensaje.set('');

    this.service.asignarRol(this.auth.token(), usuario.id, rol).subscribe({
      next: (respuesta) => {
        this.usuarios.update((lista) => lista.map((u) => (u.id === usuario.id ? respuesta.usuario : u)));
        this.seleccionados.update((sels) => {
          const copia = { ...sels };
          delete copia[usuario.id];
          return copia;
        });
        this.guardandoId.set(null);
        this.mensaje.set(`${respuesta.usuario.correo}: ${respuesta.detalle}`);
      },
      error: () => {
        this.guardandoId.set(null);
        this.error.set('No se pudo asignar el rol. Inténtalo de nuevo.');
      },
    });
  }
}
