import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectorRef,
  Component,
  OnDestroy,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { DictadoService, Escucha } from '../../../core/services/dictado.service';
import { PermisosService } from '../../../core/services/permisos.service';
import { ToastService } from '../../../core/services/toast.service';
import { PaginadorComponent } from '../../../shared/components/paginador/paginador.component';
import { AuthService } from '../../auth/auth.service';
import {
  CatalogoReportes,
  ColumnaReporte,
  ConsultaReporte,
  Direccion,
  FormatoReporte,
  FuenteReporte,
  OrdenReporte,
  ValorFiltro,
  VistaPrevia,
} from '../reportes.models';
import { ReportesService } from '../reportes.service';
import { PermisoDirective } from '../../../shared/directives/permiso.directive';

const ICONO_FUENTE: Record<string, string> = {
  egresados: '🎓',
  empresas: '🏢',
  vacantes: '💼',
  postulaciones: '📄',
};
const MAX_ORDEN = 3;
const CORREO_VALIDO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface Envio {
  formato: FormatoReporte;
  destinatarios: string;
  mensaje: string;
  enviando: boolean;
  error: string;
}

function mensajeDeError(err: HttpErrorResponse, porDefecto: string): string {
  return typeof err.error?.detail === 'string' ? err.error.detail : porDefecto;
}

/**
 * Reportes personalizados (requisito 5): el usuario elige qué reportar, filtra, elige y
 * ordena las columnas, ve la vista previa y la exporta a Excel, PDF o HTML, o la manda por correo.
 * También puede pedirlo con sus palabras, escrito o dictado: la IA arma la configuración y
 * la persona la revisa en los mismos pasos antes de exportar.
 */
@Component({
  selector: 'app-reporte-personalizado',
  standalone: true,
  imports: [FormsModule, RouterLink, PaginadorComponent, PermisoDirective],
  templateUrl: './reporte-personalizado.component.html',
  styleUrl: './reporte-personalizado.component.scss',
})
export class ReportePersonalizadoComponent implements OnInit, OnDestroy {
  private readonly servicio = inject(ReportesService);
  private readonly toast = inject(ToastService);
  private readonly dictado = inject(DictadoService);
  private readonly permisos = inject(PermisosService);
  private readonly cdr = inject(ChangeDetectorRef);
  readonly auth = inject(AuthService);

  readonly esEmpresa = computed(() => this.auth.rol() === 'empresa');
  readonly catalogo = signal<CatalogoReportes | null>(null);
  readonly cargando = signal(true);
  readonly error = signal('');

  readonly fuenteClave = signal<string | null>(null);
  readonly fuente = computed<FuenteReporte | null>(
    () => this.catalogo()?.fuentes.find((f) => f.clave === this.fuenteClave()) ?? null,
  );
  readonly columnas = signal<string[]>([]);
  readonly orden = signal<OrdenReporte[]>([]);
  filtros: Record<string, ValorFiltro> = {};
  titulo = '';

  readonly columnasDisponibles = computed(() => {
    const elegidas = new Set(this.columnas());
    return (this.fuente()?.columnas ?? []).filter((c) => !elegidas.has(c.clave));
  });

  readonly vista = signal<VistaPrevia | null>(null);
  readonly generando = signal(false);
  readonly pagina = signal(1);
  readonly tamanio = signal(25);
  private consultaGenerada: ConsultaReporte | null = null;
  readonly exportando = signal<FormatoReporte | null>(null);
  readonly envio = signal<Envio | null>(null);

  // Pedido con palabras (IA)
  readonly vozDisponible = this.dictado.disponible;
  readonly pedido = signal('');
  readonly interpretando = signal(false);
  readonly escuchando = signal(false);
  readonly explicacion = signal('');
  private escucha: Escucha | null = null;

  ngOnInit(): void {
    this.servicio.catalogo().subscribe({
      next: (catalogo) => {
        this.catalogo.set(catalogo);
        this.cargando.set(false);
        if (catalogo.fuentes.length === 1) this.elegirFuente(catalogo.fuentes[0]);
      },
      error: (err: HttpErrorResponse) => {
        this.error.set(mensajeDeError(err, 'No se pudieron cargar los reportes.'));
        this.cargando.set(false);
      },
    });
  }

  ngOnDestroy(): void {
    this.escucha?.detener();
  }

  icono(clave: string): string {
    return ICONO_FUENTE[clave] ?? '📊';
  }

  // ─── 0. Pedido con palabras ─────────────────────────────────────────────

  /** Escucha el pedido; al terminar de hablar lo manda a armar. */
  dictar(): void {
    if (this.escucha) {
      this.escucha.detener();
      return;
    }
    this.pedido.set('');
    this.escuchando.set(true);
    const escucha = this.dictado.escuchar((texto) => this.pedido.set(texto));
    this.escucha = escucha;
    escucha.resultado
      .then(
        (texto) => {
          this.pedido.set(texto);
          if (texto.length >= 3) this.armarConIA();
        },
        (err: Error) => this.toast.warning(err.message),
      )
      .finally(() => {
        this.escucha = null;
        this.escuchando.set(false);
      });
  }

  armarConIA(): void {
    const pedido = this.pedido().trim();
    if (pedido.length < 3 || this.interpretando()) return;
    this.interpretando.set(true);
    this.explicacion.set('');
    this.servicio.interpretar(pedido).subscribe({
      next: (r) => {
        this.interpretando.set(false);
        if (!this.aplicar(r.consulta)) {
          this.toast.error('No se pudo armar ese reporte. Probá con otras palabras.');
          return;
        }
        this.explicacion.set(r.explicacion);
        this.generar();
        // Si pidió el archivo («…en Excel»), se descarga como con el botón.
        if (r.formato && this.permisos.puede('boton.reportes.exportar')) this.exportar(r.formato);
        this.cdr.markForCheck();
      },
      error: (err: HttpErrorResponse) => {
        this.interpretando.set(false);
        this.toast.error(mensajeDeError(err, 'No se pudo armar el reporte. Probá de nuevo o armalo a mano.'));
      },
    });
  }

  /** Carga en los pasos de abajo la consulta que armó la IA, para revisarla y ajustarla. */
  private aplicar(consulta: ConsultaReporte): boolean {
    const fuente = this.catalogo()?.fuentes.find((f) => f.clave === consulta.fuente);
    if (!fuente) return false;
    const filtros = this.filtrosVacios(fuente);
    for (const [clave, valor] of Object.entries(consulta.filtros)) {
      if (clave in filtros) filtros[clave] = valor;
    }
    this.fuenteClave.set(fuente.clave);
    this.columnas.set(consulta.columnas);
    this.orden.set(consulta.orden.length ? consulta.orden : fuente.orden.map((o) => ({ ...o })));
    this.filtros = filtros;
    this.titulo = consulta.titulo ?? '';
    this.vista.set(null);
    this.consultaGenerada = null;
    return true;
  }

  // ─── 1. Fuente ──────────────────────────────────────────────────────────

  elegirFuente(fuente: FuenteReporte): void {
    if (this.fuenteClave() === fuente.clave) return;
    this.fuenteClave.set(fuente.clave);
    this.columnas.set(fuente.columnas.filter((c) => c.por_defecto).map((c) => c.clave));
    this.orden.set(fuente.orden.map((o) => ({ ...o })));
    this.filtros = this.filtrosVacios(fuente);
    this.titulo = '';
    this.vista.set(null);
    this.consultaGenerada = null;
  }

  // ─── 2. Filtros ─────────────────────────────────────────────────────────

  opcionElegida(filtro: string, valor: string): boolean {
    return (this.filtros[filtro] as string[]).includes(valor);
  }

  alternarOpcion(filtro: string, valor: string): void {
    const actuales = this.filtros[filtro] as string[];
    this.filtros[filtro] = actuales.includes(valor)
      ? actuales.filter((v) => v !== valor)
      : [...actuales, valor];
  }

  rango(filtro: string): { desde: string; hasta: string } {
    return this.filtros[filtro] as { desde: string; hasta: string };
  }

  numeros(filtro: string): { min: number | null; max: number | null } {
    return this.filtros[filtro] as { min: number | null; max: number | null };
  }

  private filtrosActivos(): Record<string, ValorFiltro> {
    const activos: Record<string, ValorFiltro> = {};
    for (const [clave, valor] of Object.entries(this.filtros)) {
      if (typeof valor === 'string') {
        if (valor.trim()) activos[clave] = valor.trim();
      } else if (Array.isArray(valor)) {
        if (valor.length) activos[clave] = valor;
      } else if ('desde' in valor) {
        if (valor.desde || valor.hasta) activos[clave] = { desde: valor.desde, hasta: valor.hasta };
      } else if (valor.min !== null || valor.max !== null) {
        activos[clave] = { min: valor.min, max: valor.max };
      }
    }
    return activos;
  }

  cantidadFiltros(): number {
    return Object.keys(this.filtrosActivos()).length;
  }

  limpiarFiltros(): void {
    const fuente = this.fuente();
    if (fuente) this.filtros = this.filtrosVacios(fuente);
  }

  private filtrosVacios(fuente: FuenteReporte): Record<string, ValorFiltro> {
    const vacios: Record<string, ValorFiltro> = {};
    for (const f of fuente.filtros) {
      vacios[f.clave] =
        f.tipo === 'opciones'
          ? []
          : f.tipo === 'fechas'
            ? { desde: '', hasta: '' }
            : f.tipo === 'numeros'
              ? { min: null, max: null }
              : '';
    }
    return vacios;
  }

  // ─── 3. Columnas ────────────────────────────────────────────────────────

  columna(clave: string): ColumnaReporte | undefined {
    return this.fuente()?.columnas.find((c) => c.clave === clave);
  }

  agregarColumna(clave: string): void {
    this.columnas.update((lista) => [...lista, clave]);
  }

  quitarColumna(clave: string): void {
    this.columnas.update((lista) => lista.filter((c) => c !== clave));
  }

  moverColumna(indice: number, delta: -1 | 1): void {
    this.columnas.update((lista) => {
      const destino = indice + delta;
      if (destino < 0 || destino >= lista.length) return lista;
      const copia = [...lista];
      [copia[indice], copia[destino]] = [copia[destino], copia[indice]];
      return copia;
    });
  }

  todasLasColumnas(): void {
    this.columnas.set((this.fuente()?.columnas ?? []).map((c) => c.clave));
  }

  // ─── 4. Orden ───────────────────────────────────────────────────────────

  puedeAgregarOrden(): boolean {
    return (
      this.orden().length < MAX_ORDEN && this.orden().length < (this.fuente()?.columnas.length ?? 0)
    );
  }

  agregarOrden(): void {
    const usadas = new Set(this.orden().map((o) => o.columna));
    const libre = this.fuente()?.columnas.find((c) => !usadas.has(c.clave));
    if (libre) this.orden.update((lista) => [...lista, { columna: libre.clave, direccion: 'asc' }]);
  }

  cambiarOrden(indice: number, campo: 'columna' | 'direccion', valor: string): void {
    this.orden.update((lista) =>
      lista.map((o, i) =>
        i === indice ? { ...o, [campo]: campo === 'direccion' ? (valor as Direccion) : valor } : o,
      ),
    );
  }

  quitarOrden(indice: number): void {
    this.orden.update((lista) => lista.filter((_, i) => i !== indice));
  }

  // ─── Generar y exportar ─────────────────────────────────────────────────

  private consulta(): ConsultaReporte {
    return {
      fuente: this.fuenteClave() ?? '',
      columnas: this.columnas(),
      filtros: this.filtrosActivos(),
      orden: this.orden(),
      titulo: this.titulo.trim() || null,
    };
  }

  generar(): void {
    if (!this.columnas().length) {
      this.toast.warning('Elegí al menos una columna.');
      return;
    }
    this.consultaGenerada = this.consulta();
    this.pagina.set(1);
    this.pedirPagina();
  }

  cambiarPagina(pagina: number): void {
    this.pagina.set(pagina);
    this.pedirPagina();
  }

  cambiarTamanio(tamanio: number): void {
    this.tamanio.set(tamanio);
    this.pagina.set(1);
    this.pedirPagina();
  }

  private pedirPagina(): void {
    if (!this.consultaGenerada) return;
    this.generando.set(true);
    this.servicio.vistaPrevia(this.consultaGenerada, this.pagina(), this.tamanio()).subscribe({
      next: (vista) => {
        this.vista.set(vista);
        this.generando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.generando.set(false);
        this.toast.error(mensajeDeError(err, 'No se pudo generar el reporte.'));
      },
    });
  }

  /** La configuración cambió después de generar: la vista previa ya no la refleja. */
  desactualizado(): boolean {
    return (
      !!this.consultaGenerada &&
      JSON.stringify(this.consultaGenerada) !== JSON.stringify(this.consulta())
    );
  }

  exportar(formato: FormatoReporte): void {
    if (this.exportando()) return;
    this.exportando.set(formato);
    this.servicio.exportar(this.consultaGenerada ?? this.consulta(), formato).subscribe({
      next: (respuesta) => {
        this.exportando.set(null);
        const disposicion = respuesta.headers.get('Content-Disposition') ?? '';
        const nombre =
          /filename="?([^";]+)"?/.exec(disposicion)?.[1] ??
          `reporte.${formato === 'excel' ? 'xlsx' : formato}`;
        const url = URL.createObjectURL(respuesta.body as Blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = nombre;
        enlace.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      },
      error: (err: HttpErrorResponse) => {
        this.exportando.set(null);
        // El error llega como Blob porque se pidió un archivo.
        if (err.error instanceof Blob) {
          err.error.text().then((texto) => {
            try {
              this.toast.error(JSON.parse(texto).detail ?? 'No se pudo exportar el reporte.');
            } catch {
              this.toast.error('No se pudo exportar el reporte.');
            }
          });
        } else {
          this.toast.error(mensajeDeError(err, 'No se pudo exportar el reporte.'));
        }
      },
    });
  }

  abrirEnvio(): void {
    this.envio.set({ formato: 'pdf', destinatarios: '', mensaje: '', enviando: false, error: '' });
  }

  cerrarEnvio(): void {
    if (!this.envio()?.enviando) this.envio.set(null);
  }

  actualizarEnvio(campo: 'formato' | 'destinatarios' | 'mensaje', valor: string): void {
    this.envio.update((e) => (e ? { ...e, [campo]: valor, error: '' } : e));
  }

  enviar(): void {
    const e = this.envio();
    if (!e || e.enviando) return;
    const destinatarios = e.destinatarios
      .split(/[\s,;]+/)
      .map((d) => d.trim())
      .filter(Boolean);
    const invalidos = destinatarios.filter((d) => !CORREO_VALIDO.test(d));
    if (!destinatarios.length || invalidos.length) {
      this.envio.set({
        ...e,
        error: invalidos.length ? `Revisá: ${invalidos.join(', ')}` : 'Escribí al menos un correo.',
      });
      return;
    }
    if (destinatarios.length > 10) {
      this.envio.set({ ...e, error: 'Hasta 10 destinatarios por envío.' });
      return;
    }
    this.envio.set({ ...e, enviando: true, error: '' });
    this.servicio
      .enviar(
        this.consultaGenerada ?? this.consulta(),
        e.formato,
        destinatarios,
        e.mensaje.trim() || null,
      )
      .subscribe({
        next: (r) => {
          this.envio.set(null);
          this.toast.success(r.mensaje);
        },
        error: (err: HttpErrorResponse) =>
          this.envio.set({
            ...e,
            enviando: false,
            error: mensajeDeError(err, 'No se pudo enviar el reporte.'),
          }),
      });
  }

  // ─── Formato de celdas ──────────────────────────────────────────────────

  celda(columna: ColumnaReporte, valor: unknown): string {
    if (valor === null || valor === undefined || valor === '') return '—';
    if (columna.tipo === 'fecha') {
      return new Date(String(valor)).toLocaleString('es-BO', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    }
    if (columna.tipo === 'numero') return Number(valor).toLocaleString('es-BO');
    if (typeof valor === 'boolean') return valor ? 'Sí' : 'No';
    return String(valor);
  }
}
