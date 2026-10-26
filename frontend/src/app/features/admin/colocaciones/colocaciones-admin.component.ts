import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ToastService } from '../../../core/services/toast.service';
import { PaginadorComponent } from '../../../shared/components/paginador/paginador.component';
import { PermisoDirective } from '../../../shared/directives/permiso.directive';
import { AuthService } from '../../auth/auth.service';
import { mensajeDeError } from '../../moderacion/denuncias.models';
import {
  CambioColocacion,
  Colocacion,
  EgresadoOpcion,
  EmpresaOpcion,
  ESTADO_LEGIBLE,
  EstadoColocacion,
  ORIGEN_LEGIBLE,
} from './colocaciones.models';
import { ColocacionesService } from './colocaciones.service';

/** Espera tras la última tecla antes de buscar egresados o empresas. */
const ESPERA_BUSQUEDA_MS = 300;

/** HU-29: la universidad registra las contrataciones de sus egresados y confirma las que sugiere la plataforma. */
@Component({
  selector: 'app-colocaciones-admin',
  standalone: true,
  imports: [DatePipe, FormsModule, PaginadorComponent, PermisoDirective],
  templateUrl: './colocaciones-admin.component.html',
  styleUrl: './colocaciones-admin.component.scss',
})
export class ColocacionesAdminComponent implements OnInit, OnDestroy {
  private readonly servicio = inject(ColocacionesService);
  private readonly toast = inject(ToastService);
  readonly auth = inject(AuthService);

  readonly estadoLegible = ESTADO_LEGIBLE;
  readonly origenLegible = ORIGEN_LEGIBLE;
  readonly monedas = ['BOB', 'USD'];

  // Lista
  readonly colocaciones = signal<Colocacion[]>([]);
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly total = signal(0);
  readonly sugeridas = signal(0);
  readonly pagina = signal(1);
  readonly tamanio = signal(10);
  readonly filtroEstado = signal<EstadoColocacion | ''>('');
  readonly texto = signal('');
  readonly confirmando = signal<string | null>(null);

  // Formulario de alta o edición
  readonly formularioAbierto = signal(false);
  readonly editando = signal<Colocacion | null>(null);
  readonly busquedaEgresado = signal('');
  readonly opcionesEgresado = signal<EgresadoOpcion[]>([]);
  readonly egresado = signal<EgresadoOpcion | null>(null);
  readonly empresaRegistrada = signal(true);
  readonly busquedaEmpresa = signal('');
  readonly opcionesEmpresa = signal<EmpresaOpcion[]>([]);
  readonly empresa = signal<EmpresaOpcion | null>(null);
  readonly empresaNombre = signal('');
  readonly cargo = signal('');
  readonly fechaInicio = signal('');
  readonly salario = signal('');
  readonly moneda = signal('BOB');
  readonly motivo = signal('');
  readonly guardando = signal(false);
  readonly errorFormulario = signal<string | null>(null);
  readonly puedeGuardar = computed(() => {
    if (this.guardando()) return false;
    const empresaLista = this.empresaRegistrada() ? this.empresa() !== null : this.empresaNombre().trim().length > 0;
    const base =
      this.cargo().trim().length >= 2 && this.fechaInicio() !== '' && empresaLista && this.salarioValido();
    if (this.editando()) return base && this.motivo().trim().length >= 3;
    return base && this.egresado() !== null;
  });

  // Eliminación
  readonly porEliminar = signal<Colocacion | null>(null);
  readonly motivoEliminacion = signal('');
  readonly eliminando = signal(false);
  readonly errorEliminacion = signal<string | null>(null);

  private temporizadorEgresado: ReturnType<typeof setTimeout> | undefined;
  private temporizadorEmpresa: ReturnType<typeof setTimeout> | undefined;

  ngOnInit(): void {
    this.cargar();
  }

  ngOnDestroy(): void {
    clearTimeout(this.temporizadorEgresado);
    clearTimeout(this.temporizadorEmpresa);
  }

  // ─── Lista ───────────────────────────────────────────────────────────

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.servicio
      .listar({ page: this.pagina(), pageSize: this.tamanio(), estado: this.filtroEstado(), q: this.texto() })
      .subscribe({
        next: (r) => {
          this.colocaciones.set(r.items);
          this.total.set(r.total);
          this.sugeridas.set(r.sugeridas);
          this.cargando.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.error.set(mensajeDeError(err, 'No se pudieron cargar las colocaciones.'));
          this.cargando.set(false);
        },
      });
  }

  buscar(): void {
    this.pagina.set(1);
    this.cargar();
  }

  verPorConfirmar(): void {
    this.filtroEstado.set('suggested');
    this.buscar();
  }

  irAPagina(pagina: number): void {
    this.pagina.set(pagina);
    this.cargar();
  }

  cambiarTamanio(tamanio: number): void {
    this.tamanio.set(tamanio);
    this.pagina.set(1);
    this.cargar();
  }

  monto(c: Colocacion): string {
    if (c.salario === null || c.salario === '') return '—';
    const valor = Number(c.salario).toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return `${valor} ${c.moneda ?? ''}`.trim();
  }

  // ─── Confirmar una sugerencia (CP02) ─────────────────────────────────

  confirmar(c: Colocacion): void {
    if (this.confirmando()) return;
    this.confirmando.set(c.id);
    this.servicio.confirmar(c.id).subscribe({
      next: () => {
        this.confirmando.set(null);
        this.toast.success(`Confirmaste la colocación de ${c.egresado}.`);
        this.cargar();
      },
      error: (err: HttpErrorResponse) => {
        this.confirmando.set(null);
        this.toast.error(mensajeDeError(err, 'No se pudo confirmar la colocación.'));
      },
    });
  }

  // ─── Registrar o editar (CP01 y CP03) ────────────────────────────────

  abrirAlta(): void {
    this.editando.set(null);
    this.egresado.set(null);
    this.busquedaEgresado.set('');
    this.opcionesEgresado.set([]);
    this.empresaRegistrada.set(true);
    this.empresa.set(null);
    this.busquedaEmpresa.set('');
    this.opcionesEmpresa.set([]);
    this.empresaNombre.set('');
    this.cargo.set('');
    this.fechaInicio.set('');
    this.salario.set('');
    this.moneda.set('BOB');
    this.motivo.set('');
    this.errorFormulario.set(null);
    this.formularioAbierto.set(true);
    this.buscarEgresados();
    this.buscarEmpresas();
  }

  abrirEdicion(c: Colocacion): void {
    this.editando.set(c);
    this.egresado.set(null);
    this.empresaRegistrada.set(c.empresa_id !== null);
    this.empresa.set(c.empresa_id ? { id: c.empresa_id, nombre: c.empresa } : null);
    this.busquedaEmpresa.set('');
    this.opcionesEmpresa.set([]);
    this.empresaNombre.set(c.empresa_id ? '' : c.empresa);
    this.cargo.set(c.cargo);
    this.fechaInicio.set(c.fecha_inicio);
    this.salario.set(c.salario === null ? '' : String(Number(c.salario)));
    this.moneda.set(c.moneda ?? 'BOB');
    this.motivo.set('');
    this.errorFormulario.set(null);
    this.formularioAbierto.set(true);
    this.buscarEmpresas();
  }

  cerrarFormulario(): void {
    if (!this.guardando()) this.formularioAbierto.set(false);
  }

  alEscribirEgresado(texto: string): void {
    this.busquedaEgresado.set(texto);
    clearTimeout(this.temporizadorEgresado);
    this.temporizadorEgresado = setTimeout(() => this.buscarEgresados(), ESPERA_BUSQUEDA_MS);
  }

  alEscribirEmpresa(texto: string): void {
    this.busquedaEmpresa.set(texto);
    clearTimeout(this.temporizadorEmpresa);
    this.temporizadorEmpresa = setTimeout(() => this.buscarEmpresas(), ESPERA_BUSQUEDA_MS);
  }

  private buscarEgresados(): void {
    this.servicio.buscarEgresados(this.busquedaEgresado()).subscribe({
      next: (opciones) => this.opcionesEgresado.set(opciones),
      error: () => this.opcionesEgresado.set([]),
    });
  }

  private buscarEmpresas(): void {
    this.servicio.buscarEmpresas(this.busquedaEmpresa()).subscribe({
      next: (opciones) => this.opcionesEmpresa.set(opciones),
      error: () => this.opcionesEmpresa.set([]),
    });
  }

  /** Vacío es válido (sin salario); si hay valor tiene que ser un número no negativo. */
  salarioValido(): boolean {
    const texto = this.salario().trim();
    if (texto === '') return true;
    const valor = Number(texto);
    return Number.isFinite(valor) && valor >= 0;
  }

  private salarioNumerico(): number | null {
    const texto = this.salario().trim();
    return texto === '' ? null : Number(texto);
  }

  guardar(): void {
    if (!this.puedeGuardar()) return;
    const original = this.editando();
    this.guardando.set(true);
    this.errorFormulario.set(null);

    if (original) {
      const cambio = this.cambios(original);
      if (!cambio) {
        this.guardando.set(false);
        this.errorFormulario.set('No cambiaste ningún dato de la colocación.');
        return;
      }
      this.servicio.editar(original.id, cambio).subscribe({
        next: () => this.alGuardar('Guardaste los cambios de la colocación.'),
        error: (err: HttpErrorResponse) => this.alFallar(err, 'No se pudo guardar la colocación.'),
      });
      return;
    }

    const salario = this.salarioNumerico();
    this.servicio
      .registrar({
        egresado_id: this.egresado()!.id,
        empresa_id: this.empresaRegistrada() ? this.empresa()!.id : null,
        empresa_nombre: this.empresaRegistrada() ? null : this.empresaNombre().trim(),
        cargo: this.cargo().trim(),
        fecha_inicio: this.fechaInicio(),
        salario,
        moneda: salario === null ? null : this.moneda(),
      })
      .subscribe({
        next: () => this.alGuardar('Registraste la colocación.'),
        error: (err: HttpErrorResponse) => this.alFallar(err, 'No se pudo registrar la colocación.'),
      });
  }

  /** Solo los campos que cambiaron; null si no cambió ninguno. */
  private cambios(original: Colocacion): CambioColocacion | null {
    const cambio: CambioColocacion = { motivo: this.motivo().trim() };
    let hayCambios = false;

    if (this.empresaRegistrada()) {
      const elegida = this.empresa();
      if (elegida && elegida.id !== original.empresa_id) {
        cambio.empresa_id = elegida.id;
        hayCambios = true;
      }
    } else {
      const nombre = this.empresaNombre().trim();
      if (original.empresa_id !== null || nombre !== original.empresa) {
        cambio.empresa_nombre = nombre;
        hayCambios = true;
      }
    }
    if (this.cargo().trim() !== original.cargo) {
      cambio.cargo = this.cargo().trim();
      hayCambios = true;
    }
    if (this.fechaInicio() !== original.fecha_inicio) {
      cambio.fecha_inicio = this.fechaInicio();
      hayCambios = true;
    }
    const salario = this.salarioNumerico();
    const salarioOriginal = original.salario === null ? null : Number(original.salario);
    const moneda = salario === null ? null : this.moneda();
    if (salario !== salarioOriginal) {
      cambio.salario = salario;
      cambio.moneda = moneda ?? original.moneda;
      hayCambios = true;
    } else if (salario !== null && moneda !== original.moneda) {
      cambio.moneda = moneda;
      hayCambios = true;
    }
    return hayCambios ? cambio : null;
  }

  private alGuardar(mensaje: string): void {
    this.guardando.set(false);
    this.formularioAbierto.set(false);
    this.toast.success(mensaje);
    this.cargar();
  }

  private alFallar(err: HttpErrorResponse, porDefecto: string): void {
    this.guardando.set(false);
    this.errorFormulario.set(mensajeDeError(err, porDefecto));
  }

  // ─── Eliminar (CP04) ─────────────────────────────────────────────────

  pedirEliminacion(c: Colocacion): void {
    this.motivoEliminacion.set('');
    this.errorEliminacion.set(null);
    this.porEliminar.set(c);
  }

  cancelarEliminacion(): void {
    if (!this.eliminando()) this.porEliminar.set(null);
  }

  confirmarEliminacion(): void {
    const c = this.porEliminar();
    const motivo = this.motivoEliminacion().trim();
    if (!c || this.eliminando() || motivo.length < 3) return;
    this.eliminando.set(true);
    this.errorEliminacion.set(null);
    this.servicio.eliminar(c.id, motivo).subscribe({
      next: () => {
        this.eliminando.set(false);
        this.porEliminar.set(null);
        this.toast.success(`Eliminaste la colocación de ${c.egresado}.`);
        this.cargar();
      },
      error: (err: HttpErrorResponse) => {
        this.eliminando.set(false);
        this.errorEliminacion.set(mensajeDeError(err, 'No se pudo eliminar la colocación.'));
      },
    });
  }
}
