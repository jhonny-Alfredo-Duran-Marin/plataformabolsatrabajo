import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import {
  InstitucionDisponible,
  Plan,
  SolicitudUniversidad,
  textoLimite,
  textoPrecio,
} from '../../../core/models/plan.models';
import { PlanesService } from '../../../core/services/planes.service';

const OTRA = 'otra';
const PLAN_RECOMENDADO = 'profesional';

/**
 * Página pública donde una universidad elige un plan y pide su alta en el SaaS.
 * El superadmin la revisa; al aprobarla se crea el admin con una contraseña temporal.
 */
@Component({
  selector: 'app-registro-universidad',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './registro-universidad.html',
  styleUrl: './registro-universidad.scss',
})
export class RegistroUniversidad implements OnInit {
  private readonly planesService = inject(PlanesService);

  readonly OTRA = OTRA;
  readonly recomendado = PLAN_RECOMENDADO;
  readonly textoLimite = textoLimite;
  readonly textoPrecio = textoPrecio;

  readonly planes = signal<Plan[]>([]);
  readonly disponibles = signal<InstitucionDisponible[]>([]);
  readonly cargando = signal(true);
  readonly enviando = signal(false);
  readonly error = signal('');
  readonly enviada = signal<SolicitudUniversidad | null>(null);

  readonly plan = signal(PLAN_RECOMENDADO);
  readonly catalogo = signal(''); // id de una universidad del catálogo, OTRA o vacío
  nombre = '';
  sigla = '';
  ciudad = '';
  responsableNombre = '';
  responsableCorreo = '';
  responsableTelefono = '';

  // Variables de pasarela de pago (visuales para la presentacion)
  metodoPago = signal<'tarjeta' | 'qr'>('tarjeta');
  numeroTarjeta = '';
  vencimientoTarjeta = '';
  cvvTarjeta = '';

  readonly planElegido = computed(() => this.planes().find((p) => p.codigo === this.plan()));

  ngOnInit(): void {
    this.planesService.listarPlanes().subscribe({
      next: (planes) => {
        this.planes.set(planes);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudieron cargar los planes. Verificá tu conexión e intentá de nuevo.');
        this.cargando.set(false);
      },
    });
    this.planesService.institucionesDisponibles().subscribe({
      next: (lista) => this.disponibles.set(lista),
      error: () => this.disponibles.set([]),
    });
  }

  elegirDelCatalogo(valor: string): void {
    this.catalogo.set(valor);
    const inst = this.disponibles().find((i) => i.id === valor);
    if (inst) {
      this.nombre = inst.nombre;
      this.ciudad = inst.ciudad ?? '';
    } else if (valor === OTRA) {
      this.nombre = '';
      this.ciudad = '';
    }
  }

  enviar(): void {
    if (this.enviando()) return;
    const faltante = this.validar();
    if (faltante) {
      this.error.set(faltante); window.scrollTo({ top: 0, behavior: 'smooth' }); return;
    }

    this.enviando.set(true);
    this.error.set('');
    const delCatalogo = this.disponibles().some((i) => i.id === this.catalogo());
    this.planesService
      .solicitarAlta({
        institucion_id: delCatalogo ? this.catalogo() : null,
        nombre: this.nombre.trim(),
        sigla: this.sigla.trim().toUpperCase(),
        ciudad: this.ciudad.trim() || null,
        responsable_nombre: this.responsableNombre.trim(),
        responsable_correo: this.responsableCorreo.trim(),
        responsable_telefono: this.responsableTelefono.trim() || null,
        plan: this.plan(),
      })
      .subscribe({
        next: (solicitud) => {
          this.enviando.set(false);
          this.enviada.set(solicitud);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        },
        error: (err: HttpErrorResponse) => {
          this.enviando.set(false);
          this.error.set(
            typeof err.error?.detail === 'string'
              ? err.error.detail
              : 'No se pudo enviar la solicitud. Revisá los datos e intentá de nuevo.',
          );
        },
      });
  }

  private validar(): string | null {
    if (!this.catalogo()) return 'Elegí tu universidad de la lista o la opción "Otra".';
    if (this.nombre.trim().length < 3) return 'Ingresá el nombre de la universidad.';
    if (!/^[A-Za-z0-9-]{2,20}$/.test(this.sigla.trim())) return 'La sigla debe tener entre 2 y 20 letras o números (ej. UPDS).';
    if (this.responsableNombre.trim().length < 3) return 'Ingresá el nombre del responsable.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.responsableCorreo.trim())) return 'Ingresá un correo válido para el responsable.';
    if (this.plan() !== 'basico' && this.metodoPago() === 'tarjeta') { if (this.numeroTarjeta.trim().length < 15) return 'Por favor, ingres� un n�mero de tarjeta v�lido.'; if (this.vencimientoTarjeta.trim().length < 4) return 'Por favor, ingres� el vencimiento de tu tarjeta.'; if (this.cvvTarjeta.trim().length < 3) return 'Ingres� el CVV de tu tarjeta.'; } return null;
  }
}


