import { DatePipe } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { environment } from '../../../../environments/environment';
import { ToastService } from '../../../core/services/toast.service';
import { PaginadorComponent } from '../../../shared/components/paginador/paginador.component';
import { PermisoDirective } from '../../../shared/directives/permiso.directive';
import { AuthService } from '../../auth/auth.service';
import { mensajeDeError } from '../../moderacion/denuncias.models';
import { ALCANCE_LEGIBLE, AvanceEncuesta, Encuesta } from '../../encuestas/encuestas.models';
import { EncuestasService } from '../../encuestas/encuestas.service';

interface Carrera {
  id: string;
  nombre: string;
}

/** HU-30: el administrador envía la encuesta de situación laboral y sigue cuántos egresados respondieron. */
@Component({
  selector: 'app-encuestas-admin',
  standalone: true,
  imports: [DatePipe, FormsModule, PaginadorComponent, PermisoDirective],
  templateUrl: './encuestas-admin.component.html',
  styleUrl: './encuestas-admin.component.scss',
})
export class EncuestasAdminComponent implements OnInit {
  private readonly servicio = inject(EncuestasService);
  private readonly http = inject(HttpClient);
  private readonly toast = inject(ToastService);
  readonly auth = inject(AuthService);

  readonly alcanceLegible = ALCANCE_LEGIBLE;
  /** Hoy en formato AAAA-MM-DD: la fecha de cierre no puede ser anterior. */
  readonly hoy = new Date().toISOString().slice(0, 10);

  readonly encuestas = signal<Encuesta[]>([]);
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly total = signal(0);
  readonly pagina = signal(1);
  readonly tamanio = signal(10);

  // Avance de una encuesta abierta en la lista
  readonly avance = signal<AvanceEncuesta | null>(null);
  readonly cargandoAvance = signal<string | null>(null);
  readonly mayorCantidad = computed(() =>
    Math.max(1, ...(this.avance()?.situacion_laboral ?? []).map((s) => s.cantidad)),
  );

  // Formulario de una encuesta nueva
  readonly formularioAbierto = signal(false);
  readonly carreras = signal<Carrera[]>([]);
  readonly titulo = signal('');
  readonly descripcion = signal('');
  readonly periodo = signal('');
  readonly carreraId = signal('');
  readonly venceEl = signal('');
  readonly enviando = signal(false);
  readonly errorFormulario = signal<string | null>(null);
  readonly puedeEnviar = computed(
    () => !this.enviando() && this.titulo().trim().length >= 3 && this.periodo().trim().length > 0,
  );

  // Cierre
  readonly porCerrar = signal<Encuesta | null>(null);
  readonly cerrando = signal(false);
  readonly errorCierre = signal<string | null>(null);

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.servicio.listar(this.pagina(), this.tamanio()).subscribe({
      next: (r) => {
        this.encuestas.set(r.items);
        this.total.set(r.total);
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err, 'No se pudieron cargar las encuestas.'));
        this.cargando.set(false);
      },
    });
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

  // ─── Avance ──────────────────────────────────────────────────────────

  alternarAvance(encuesta: Encuesta): void {
    if (this.avance()?.encuesta.id === encuesta.id) {
      this.avance.set(null);
      return;
    }
    this.cargandoAvance.set(encuesta.id);
    this.servicio.avance(encuesta.id).subscribe({
      next: (a) => {
        this.avance.set(a);
        this.cargandoAvance.set(null);
      },
      error: (err: HttpErrorResponse) => {
        this.cargandoAvance.set(null);
        this.toast.error(mensajeDeError(err, 'No se pudo cargar el avance de la encuesta.'));
      },
    });
  }

  anchoBarra(cantidad: number): number {
    return Math.round((100 * cantidad) / this.mayorCantidad());
  }

  // ─── Nueva encuesta ──────────────────────────────────────────────────

  abrirFormulario(): void {
    this.titulo.set('Encuesta de situación laboral');
    this.descripcion.set('');
    this.periodo.set('');
    this.carreraId.set('');
    this.venceEl.set('');
    this.errorFormulario.set(null);
    this.formularioAbierto.set(true);
    if (this.carreras().length === 0) {
      this.http.get<Carrera[]>(`${environment.apiUrl}/catalogos/carreras`).subscribe({
        next: (carreras) => this.carreras.set(carreras),
        // Sin el catálogo igual se puede enviar a toda la universidad.
        error: () => this.carreras.set([]),
      });
    }
  }

  cerrarFormulario(): void {
    if (!this.enviando()) this.formularioAbierto.set(false);
  }

  enviar(): void {
    if (!this.puedeEnviar()) return;
    this.enviando.set(true);
    this.errorFormulario.set(null);
    this.servicio
      .enviar({
        titulo: this.titulo().trim(),
        descripcion: this.descripcion().trim() || null,
        periodo: this.periodo().trim(),
        carrera_id: this.carreraId() || null,
        vence_el: this.venceEl() || null,
      })
      .subscribe({
        next: (r) => {
          this.enviando.set(false);
          this.formularioAbierto.set(false);
          this.toast.success(r.mensaje);
          this.pagina.set(1);
          this.avance.set(null);
          this.cargar();
        },
        error: (err: HttpErrorResponse) => {
          this.enviando.set(false);
          this.errorFormulario.set(
            mensajeDeError(err, 'No se pudo enviar la encuesta. Probá de nuevo.'),
          );
        },
      });
  }

  // ─── Cierre ──────────────────────────────────────────────────────────

  pedirCierre(encuesta: Encuesta): void {
    this.errorCierre.set(null);
    this.porCerrar.set(encuesta);
  }

  cancelarCierre(): void {
    if (!this.cerrando()) this.porCerrar.set(null);
  }

  confirmarCierre(): void {
    const encuesta = this.porCerrar();
    if (!encuesta || this.cerrando()) return;
    this.cerrando.set(true);
    this.servicio.cerrar(encuesta.id).subscribe({
      next: () => {
        this.cerrando.set(false);
        this.porCerrar.set(null);
        this.toast.success(`Cerraste la encuesta del período ${encuesta.periodo}.`);
        this.avance.set(null);
        this.cargar();
      },
      error: (err: HttpErrorResponse) => {
        this.cerrando.set(false);
        this.errorCierre.set(mensajeDeError(err, 'No se pudo cerrar la encuesta.'));
      },
    });
  }
}
