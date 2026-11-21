import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { PermisosService } from '../../../core/services/permisos.service';
import { AuthService } from '../../auth/auth.service';
import { ETIQUETAS_ROL, UniversidadCliente } from '../gestion-roles/gestion-roles.model';
import { GestionRolesService } from '../gestion-roles/gestion-roles.service';
import { CatalogoPermisos, Componente, ETIQUETAS_TIPO, Grupo, Personal } from './grupos.model';
import { GruposService } from './grupos.service';

interface Modulo {
  nombre: string;
  componentes: Componente[];
}

interface Editor {
  id: string | null;
  nombre: string;
  descripcion: string;
  institucionId: string | null;
  permisos: ReadonlySet<string>;
  miembros: ReadonlySet<string>;
}

function mensajeDeError(err: HttpErrorResponse, porDefecto: string): string {
  return typeof err.error?.detail === 'string' ? err.error.detail : porDefecto;
}

/** Requisito general 2: grupos de usuarios y privilegios sobre cada componente del panel. */
@Component({
  selector: 'app-grupos',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './grupos.component.html',
  styleUrl: './grupos.component.scss',
})
export class GruposComponent implements OnInit {
  private readonly servicio = inject(GruposService);
  private readonly roles = inject(GestionRolesService);
  private readonly permisos = inject(PermisosService);
  readonly auth = inject(AuthService);

  readonly etiquetasRol = ETIQUETAS_ROL;
  readonly etiquetasTipo = ETIQUETAS_TIPO;
  readonly esSuperadmin = computed(() => !this.auth.institucion());

  readonly catalogo = signal<CatalogoPermisos | null>(null);
  readonly grupos = signal<Grupo[]>([]);
  readonly personal = signal<Personal[]>([]);
  readonly universidades = signal<UniversidadCliente[]>([]);
  /** Universidad elegida por el superadmin; el admin de una universidad siempre ve la suya. */
  readonly universidadId = signal<string | null>(null);

  readonly cargando = signal(true);
  readonly cargandoPersonal = signal(false);
  readonly error = signal('');
  readonly mensaje = signal('');

  readonly editor = signal<Editor | null>(null);
  readonly personalEditor = signal<Personal[]>([]);
  readonly filtroMiembros = signal('');
  /** Miembros al abrir el editor: van primero, sin saltar de lugar al marcar o desmarcar. */
  private readonly miembrosAlAbrir = signal<ReadonlySet<string>>(new Set());
  readonly personalFiltrado = computed(() => {
    const texto = this.filtroMiembros().trim().toLowerCase();
    const primeros = this.miembrosAlAbrir();
    return this.personalEditor()
      .filter((p) => !texto || p.correo.toLowerCase().includes(texto))
      .sort((a, b) => Number(primeros.has(b.id)) - Number(primeros.has(a.id)));
  });
  readonly guardando = signal(false);
  readonly errorEditor = signal('');
  readonly confirmandoBorrado = signal(false);
  readonly viendo = signal<Personal | null>(null);

  readonly modulos = computed<Modulo[]>(() => {
    const modulos: Modulo[] = [];
    for (const componente of this.catalogo()?.componentes ?? []) {
      const modulo = modulos.find((m) => m.nombre === componente.modulo);
      if (modulo) modulo.componentes.push(componente);
      else modulos.push({ nombre: componente.modulo, componentes: [componente] });
    }
    return modulos;
  });

  readonly totalComponentes = computed(() => this.catalogo()?.componentes.length ?? 0);
  readonly puedeVerPersonal = computed(() => !this.esSuperadmin() || !!this.universidadId());

  ngOnInit(): void {
    this.servicio.catalogo().subscribe({
      next: (catalogo) => this.catalogo.set(catalogo),
      error: (err: HttpErrorResponse) =>
        this.error.set(mensajeDeError(err, 'No se pudo cargar el catálogo de permisos.')),
    });
    if (this.esSuperadmin()) {
      this.roles
        .listarUniversidades()
        .subscribe({ next: (lista) => this.universidades.set(lista) });
    }
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set('');
    const universidad = this.universidadId();
    this.servicio.listar(universidad).subscribe({
      next: (grupos) => {
        this.grupos.set(grupos);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err, 'No se pudieron cargar los grupos.'));
        this.cargando.set(false);
      },
    });
    this.personal.set([]);
    if (this.puedeVerPersonal()) {
      this.cargandoPersonal.set(true);
      this.servicio.personal(universidad).subscribe({
        next: (lista) => {
          this.personal.set(lista);
          this.cargandoPersonal.set(false);
        },
        error: () => this.cargandoPersonal.set(false),
      });
    }
  }

  elegirUniversidad(id: string | null): void {
    this.universidadId.set(id || null);
    this.mensaje.set('');
    this.cargar();
  }

  // ─── Editor ───────────────────────────────────────────────────────────

  nuevo(): void {
    this.abrir({
      id: null,
      nombre: '',
      descripcion: '',
      institucionId: this.universidadId(),
      permisos: new Set(),
      miembros: new Set(),
    });
  }

  editar(grupo: Grupo): void {
    this.abrir({
      id: grupo.id,
      nombre: grupo.nombre,
      descripcion: grupo.descripcion ?? '',
      institucionId: grupo.institucion_id,
      permisos: new Set(grupo.permisos),
      miembros: new Set(grupo.miembros.map((m) => m.id)),
    });
  }

  private abrir(editor: Editor): void {
    this.editor.set(editor);
    this.miembrosAlAbrir.set(editor.miembros);
    this.filtroMiembros.set('');
    this.errorEditor.set('');
    this.confirmandoBorrado.set(false);
    this.cargarPersonalEditor(editor.institucionId);
  }

  private cargarPersonalEditor(institucionId: string | null): void {
    if (this.esSuperadmin() && !institucionId) {
      this.personalEditor.set([]);
      return;
    }
    this.servicio.personal(this.esSuperadmin() ? institucionId : null).subscribe({
      next: (lista) => this.personalEditor.set(lista),
      error: () => this.errorEditor.set('No se pudo cargar el personal de la universidad.'),
    });
  }

  cerrar(): void {
    this.editor.set(null);
  }

  actualizar(cambios: Partial<Editor>): void {
    this.editor.update((e) => (e ? { ...e, ...cambios } : e));
  }

  elegirUniversidadEditor(id: string | null): void {
    // Los miembros son de una universidad: al cambiarla se vacían.
    this.actualizar({ institucionId: id || null, miembros: new Set() });
    this.cargarPersonalEditor(id || null);
  }

  tienePermiso(codigo: string): boolean {
    return this.editor()?.permisos.has(codigo) ?? false;
  }

  alternarPermiso(codigo: string): void {
    const actuales = new Set(this.editor()?.permisos);
    if (actuales.has(codigo)) actuales.delete(codigo);
    else actuales.add(codigo);
    this.actualizar({ permisos: actuales });
  }

  estadoModulo(modulo: Modulo): 'todo' | 'parte' | 'nada' {
    const marcados = modulo.componentes.filter((c) => this.tienePermiso(c.codigo)).length;
    if (marcados === 0) return 'nada';
    return marcados === modulo.componentes.length ? 'todo' : 'parte';
  }

  alternarModulo(modulo: Modulo): void {
    const actuales = new Set(this.editor()?.permisos);
    const marcar = this.estadoModulo(modulo) !== 'todo';
    for (const c of modulo.componentes) {
      if (marcar) actuales.add(c.codigo);
      else actuales.delete(c.codigo);
    }
    this.actualizar({ permisos: actuales });
  }

  /** Punto de partida: lo que el rol ve sin grupos. */
  copiarRol(rol: 'platform_admin' | 'moderator'): void {
    const codigos = (this.catalogo()?.componentes ?? [])
      .filter((c) => c.por_defecto.includes(rol))
      .map((c) => c.codigo);
    this.actualizar({ permisos: new Set(codigos) });
  }

  limpiarPermisos(): void {
    this.actualizar({ permisos: new Set() });
  }

  esMiembro(id: string): boolean {
    return this.editor()?.miembros.has(id) ?? false;
  }

  alternarMiembro(id: string): void {
    const actuales = new Set(this.editor()?.miembros);
    if (actuales.has(id)) actuales.delete(id);
    else actuales.add(id);
    this.actualizar({ miembros: actuales });
  }

  soloAdmins(componente: Componente): boolean {
    return !componente.asignable_a.includes('moderator');
  }

  guardar(): void {
    const e = this.editor();
    if (!e) return;
    const nombre = e.nombre.trim();
    if (nombre.length < 3) {
      this.errorEditor.set('Poné un nombre de al menos 3 caracteres.');
      return;
    }
    if (this.esSuperadmin() && !e.institucionId) {
      this.errorEditor.set('Elegí la universidad del grupo.');
      return;
    }
    const datos = {
      nombre,
      descripcion: e.descripcion.trim() || null,
      institucion_id: this.esSuperadmin() ? e.institucionId : null,
      permisos: [...e.permisos],
      miembros: [...e.miembros],
    };
    this.guardando.set(true);
    this.errorEditor.set('');
    const peticion = e.id ? this.servicio.actualizar(e.id, datos) : this.servicio.crear(datos);
    peticion.subscribe({
      next: (grupo) => {
        this.guardando.set(false);
        this.editor.set(null);
        this.mensaje.set(
          e.id
            ? `Guardaste los cambios de «${grupo.nombre}».`
            : `Creaste el grupo «${grupo.nombre}».`,
        );
        this.alCambiar();
      },
      error: (err: HttpErrorResponse) => {
        this.guardando.set(false);
        this.errorEditor.set(mensajeDeError(err, 'No se pudo guardar el grupo.'));
      },
    });
  }

  eliminar(): void {
    const e = this.editor();
    if (!e?.id) return;
    this.guardando.set(true);
    this.servicio.eliminar(e.id).subscribe({
      next: () => {
        this.guardando.set(false);
        this.editor.set(null);
        this.mensaje.set(
          `Eliminaste el grupo «${e.nombre}». Sus miembros vuelven a ver lo de su rol.`,
        );
        this.alCambiar();
      },
      error: (err: HttpErrorResponse) => {
        this.guardando.set(false);
        this.errorEditor.set(mensajeDeError(err, 'No se pudo eliminar el grupo.'));
      },
    });
  }

  /** Los permisos efectivos cambian al instante, también los propios (el menú se actualiza). */
  private alCambiar(): void {
    this.cargar();
    this.permisos.refrescar().subscribe();
  }

  // ─── Permisos efectivos de una persona ──────────────────────────────────

  ver(persona: Personal): void {
    this.viendo.set(persona);
  }

  cerrarVista(): void {
    this.viendo.set(null);
  }
}
