import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { environment } from '../../../../environments/environment';
import { PaginadorComponent, paginar } from '../../../shared/components/paginador/paginador.component';
import { AuthService } from '../../auth/auth.service';
import { BitacoraClaveService } from '../bitacora/bitacora-clave.service';
import { BitacoraService } from '../bitacora/bitacora.service';
import { ETIQUETAS_ROL } from '../gestion-roles/gestion-roles.model';
import { PANTALLAS_ADMIN } from '../../../core/guards/permiso.guard';
import { PermisosService } from '../../../core/services/permisos.service';
import { PermisoDirective } from '../../../shared/directives/permiso.directive';

interface ResumenUniversidad {
  id: string;
  nombre: string;
  sigla: string | null;
  ciudad: string | null;
  egresados_total: number;
  egresados_verificados: number;
  egresados_pendientes: number;
  empresas_aprobadas: number;
  empresas_pendientes: number;
  vacantes_publicadas: number;
  postulaciones: number;
  plan?: { nombre: string; estado_pago: string } | null;
}

interface ActividadApi {
  fecha: string;
  usuario: string | null;
  modulo: string;
  accion: string;
  detalles: string | null;
  resultado: boolean;
}

interface PanelAdmin {
  universidades: ResumenUniversidad[];
  /** null si el grupo del usuario no ve los indicadores. */
  totales: {
    egresados: number;
    egresados_verificados: number;
    empresas_habilitadas: number;
    vacantes_publicadas: number;
    postulaciones: number;
  } | null;
  pendientes: {
    egresados: number;
    empresas: number;
    vacantes: number;
    universidades: number;
    respaldo: number;
    denuncias: number;
  };
  accesos_hoy: number;
  accesos_fallidos_hoy: number;
  actividad: ActividadApi[];
  /** Bitácora cifrada: la actividad se pide a /bitacora con la clave de desarrollador. */
  bitacora_protegida?: boolean;
}

type Tono = 'exito' | 'peligro' | 'info' | 'neutro';

interface Tarea {
  clave: 'universidades' | 'respaldos' | 'egresados' | 'empresas' | 'vacantes' | 'denuncias';
  titulo: string;
  ayuda: string;
  cantidad: number;
  ruta: string;
  query: Record<string, string> | null;
}

interface Kpi {
  etiqueta: string;
  valor: number;
  detalle: string;
  progreso?: number;
}

interface Actividad {
  texto: string;
  usuario: string | null;
  hace: string;
  fechaCompleta: string;
  tono: Tono;
}

const TEXTO_ACCION: Record<string, string> = {
  exportar_reporte: 'Exportó un reporte personalizado',
  enviar_reporte: 'Envió un reporte por correo',
  respaldo_automatico: 'Se hizo la copia de seguridad diaria',
  cerrar_vacantes_vencidas: 'Se cerraron las vacantes vencidas',
  boletin_ofertas: 'Se envió el boletín diario de ofertas',
  recordatorios: 'Se enviaron los recordatorios de cierres y entrevistas',
  ejecutar_tarea: 'Ejecutó una tarea automática a mano',
  abrir_bitacora: 'Abrió la bitácora confidencial',
  clave_bitacora_incorrecta: 'Intentó abrir la bitácora con una clave incorrecta',
  decidir_egresado: 'Revisó la validación de un egresado',
  decidir_empresa: 'Revisó la verificación de una empresa',
  suspender_empresa: 'Suspendió una empresa',
  eliminar_empresa_logico: 'Dio de baja una empresa',
  restaurar_empresa: 'Reactivó una empresa',
  configurar_empresa: 'Cambió los permisos de una empresa',
  moderate_job_posting: 'Moderó una oferta laboral',
  create_job_posting: 'Creó una oferta laboral',
  update_job_posting: 'Editó una oferta laboral',
  change_job_status: 'Cambió el estado de una oferta',
  delete_job_posting: 'Eliminó una oferta laboral',
  asignar_rol: 'Cambió el rol de un usuario',
  crear_usuario: 'Creó una cuenta institucional',
  cambiar_password: 'Cambió su contraseña',
  registro_egresado: 'Se registró un nuevo egresado',
  registro_empresa: 'Se registró una nueva empresa',
  configurar_etapas: 'Configuró las etapas de selección de una vacante',
  solicitud_universidad: 'Una universidad pidió sumarse a EGRESA',
  aprobar_universidad: 'Aprobó el alta de una universidad',
  rechazar_universidad: 'Rechazó el alta de una universidad',
  cambiar_plan: 'Cambió el plan de una universidad',
  registrar_pago: 'Registró el pago manual de un plan',
  pago_stripe: 'Pagó el plan con tarjeta',
  crear_respaldo: 'Creó una copia de seguridad',
  descargar_respaldo: 'Descargó una copia de seguridad',
  subir_respaldo: 'Subió una copia de seguridad',
  eliminar_respaldo: 'Eliminó una copia de seguridad',
  verificar_respaldo: 'Verificó una copia de seguridad',
  restaurar_respaldo: 'Restauró la plataforma desde una copia',
  avanzar_etapa: 'Avanzó a un candidato de etapa',
  descartar_candidato: 'Descartó a un candidato',
  comparar_candidatos: 'Comparó candidatos de una vacante',
  retirar_postulacion: 'Retiró una postulación',
};

const ACCIONES_NEGATIVAS = new Set([
  'suspender_empresa',
  'eliminar_empresa_logico',
  'delete_job_posting',
  'descartar_candidato',
  'retirar_postulacion',
]);

/** Lee un valor `clave=valor` de los detalles que guarda la bitácora. */
function dato(detalles: string | null, clave: string): string | null {
  const encontrado = detalles?.match(new RegExp(`(?:^|\\s)${clave}=(\\S+)`));
  return encontrado ? encontrado[1] : null;
}

function haceCuanto(fecha: Date): string {
  const minutos = Math.floor((Date.now() - fecha.getTime()) / 60000);
  if (minutos < 1) return 'hace un momento';
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;
  const dias = Math.floor(horas / 24);
  if (dias < 7) return dias === 1 ? 'ayer' : `hace ${dias} días`;
  return fecha.toLocaleDateString('es-BO', { day: 'numeric', month: 'short' });
}

function describir(a: ActividadApi): Actividad {
  const fecha = new Date(a.fecha);
  let texto = TEXTO_ACCION[a.accion] ?? a.accion.replaceAll('_', ' ');
  let tono: Tono = 'neutro';

  const aprobado = dato(a.detalles, 'aprobado');
  if (aprobado !== null && (a.accion === 'decidir_egresado' || a.accion === 'decidir_empresa')) {
    const sujeto = a.accion === 'decidir_egresado' ? 'un egresado' : 'una empresa';
    texto = aprobado === 'True' ? `Aprobó a ${sujeto}` : `Rechazó a ${sujeto}`;
    tono = aprobado === 'True' ? 'exito' : 'peligro';
  } else if (a.accion === 'asignar_rol') {
    const usuario = dato(a.detalles, 'usuario');
    const rol = dato(a.detalles, 'rol_nuevo');
    if (usuario && rol) texto = `Asignó el rol ${ETIQUETAS_ROL[rol] ?? rol} a ${usuario}`;
    tono = 'info';
  } else if (a.accion === 'crear_usuario') {
    const usuario = dato(a.detalles, 'usuario');
    const rol = dato(a.detalles, 'rol');
    if (usuario && rol) texto = `Creó la cuenta de ${ETIQUETAS_ROL[rol] ?? rol} ${usuario}`;
    tono = 'info';
  } else if (a.accion === 'solicitud_universidad' || a.accion === 'aprobar_universidad') {
    const sigla = dato(a.detalles, 'sigla');
    if (sigla) texto = `${TEXTO_ACCION[a.accion]} (${sigla})`;
    tono = a.accion === 'aprobar_universidad' ? 'exito' : 'info';
  } else if (['registrar_pago', 'pago_stripe', 'crear_respaldo', 'verificar_respaldo'].includes(a.accion)) {
    tono = 'exito';
  } else if (a.accion === 'rechazar_universidad' || a.accion === 'restaurar_respaldo') {
    tono = 'peligro';
  } else if (a.accion.startsWith('registro_')) {
    tono = 'info';
  } else if (ACCIONES_NEGATIVAS.has(a.accion)) {
    tono = 'peligro';
  }

  if (!a.resultado) {
    texto = `${texto} (falló)`;
    tono = 'peligro';
  }

  return { texto, usuario: a.usuario, hace: haceCuanto(fecha), fechaCompleta: fecha.toLocaleString('es-BO'), tono };
}

function porcentaje(parte: number, total: number): number {
  return total > 0 ? Math.round((parte / total) * 100) : 0;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, PaginadorComponent, PermisoDirective],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly bitacora = inject(BitacoraService);
  private readonly bitacoraClave = inject(BitacoraClaveService);
  readonly auth = inject(AuthService);
  private readonly permisos = inject(PermisosService);

  readonly panel = signal<PanelAdmin | null>(null);
  readonly cargando = signal(true);
  readonly error = signal('');

  readonly paginaUniversidades = signal(1);
  readonly tamanioUniversidades = signal(5);

  readonly esSuperadmin = computed(() => !this.auth.institucion());
  readonly porcentaje = porcentaje;
  /** Plan de la universidad del admin (el superadmin no tiene uno propio). */
  readonly planPropio = computed(() => (this.esSuperadmin() ? null : (this.panel()?.universidades[0]?.plan ?? null)));

  readonly saludo = computed(() => {
    const hora = new Date().getHours();
    if (hora < 12) return 'Buenos días';
    if (hora < 19) return 'Buenas tardes';
    return 'Buenas noches';
  });

  readonly tareas = computed<Tarea[]>(() => {
    const p = this.panel();
    if (!p) return [];
    const superadmin = this.esSuperadmin();
    const tareas: Tarea[] = [];
    if (superadmin) {
      tareas.push({
        clave: 'universidades',
        titulo: 'Universidades por aprobar',
        ayuda: 'Pidieron sumarse a EGRESA y eligieron un plan.',
        cantidad: p.pendientes.universidades,
        ruta: '/admin/universidades',
        query: null,
      });
      tareas.push({
        clave: 'respaldos',
        titulo: 'Copia de seguridad',
        ayuda: 'No hay copias de la última semana. Hacé una ahora.',
        cantidad: p.pendientes.respaldo,
        ruta: '/admin/respaldos',
        query: null,
      });
    }
    const todas: Tarea[] = [
      ...tareas,
      {
        clave: 'egresados',
        titulo: 'Egresados por validar',
        ayuda: 'Se registraron y esperan la verificación institucional.',
        cantidad: p.pendientes.egresados,
        ruta: '/admin/validacion-egresados',
        query: null,
      },
      {
        clave: 'empresas',
        titulo: superadmin ? 'Empresas por verificar' : 'Empresas que piden reclutar',
        ayuda: superadmin
          ? 'Empresas nuevas esperando la verificación de la plataforma.'
          : 'Solicitan acceso para reclutar egresados de tu universidad.',
        cantidad: p.pendientes.empresas,
        ruta: '/admin/empresas',
        query: { filtro: 'PENDIENTES' },
      },
      {
        clave: 'vacantes',
        titulo: 'Ofertas por moderar',
        ayuda: 'Vacantes enviadas a revisión antes de publicarse.',
        cantidad: p.pendientes.vacantes,
        ruta: '/admin/moderacion-vacantes',
        query: null,
      },
      {
        clave: 'denuncias',
        titulo: 'Ofertas denunciadas',
        ayuda: 'Usuarios reportaron ofertas sospechosas. Con 3 denuncias se ocultan hasta que decidas.',
        cantidad: p.pendientes.denuncias,
        ruta: '/admin/denuncias',
        query: null,
      },
    ];
    return todas.filter((tarea) => {
      // Solo lo pendiente de los módulos que el grupo del usuario puede abrir.
      const pantalla = PANTALLAS_ADMIN.find((p) => p.ruta === tarea.ruta);
      return !pantalla || this.permisos.puede(pantalla.permiso);
    });
  });

  readonly totalPendientes = computed(() => this.tareas().reduce((suma, t) => suma + t.cantidad, 0));

  readonly kpis = computed<Kpi[]>(() => {
    const p = this.panel();
    if (!p?.totales) return [];
    const t = p.totales;
    const superadmin = this.esSuperadmin();
    const lista: Kpi[] = [];
    if (superadmin) {
      lista.push({
        etiqueta: 'Universidades clientes',
        valor: p.universidades.length,
        detalle: 'cada una con sus datos aislados',
      });
    }
    lista.push(
      {
        etiqueta: 'Egresados',
        valor: t.egresados,
        detalle: `${t.egresados_verificados} verificados (${porcentaje(t.egresados_verificados, t.egresados)}%)`,
        progreso: porcentaje(t.egresados_verificados, t.egresados),
      },
      {
        etiqueta: 'Empresas habilitadas',
        valor: t.empresas_habilitadas,
        detalle: superadmin ? 'reclutan en al menos una universidad' : 'pueden reclutar en tu universidad',
      },
      {
        etiqueta: 'Vacantes publicadas',
        valor: t.vacantes_publicadas,
        detalle: 'visibles para los egresados',
      },
      {
        etiqueta: 'Postulaciones',
        valor: t.postulaciones,
        detalle:
          t.vacantes_publicadas > 0
            ? `≈ ${(t.postulaciones / t.vacantes_publicadas).toFixed(1)} por vacante publicada`
            : 'todavía no hay vacantes publicadas',
      },
    );
    return lista;
  });

  readonly universidadesPagina = computed(() =>
    paginar(this.panel()?.universidades ?? [], this.paginaUniversidades(), this.tamanioUniversidades()),
  );

  /** Con la bitácora cifrada, la actividad que se descifró con la clave ingresada en esta sesión. */
  readonly actividadProtegida = signal<ActividadApi[] | null>(null);
  readonly bitacoraBloqueada = computed(() => !!this.panel()?.bitacora_protegida && !this.bitacoraClave.clave());

  readonly actividad = computed(() => {
    const panel = this.panel();
    const lista = panel?.bitacora_protegida ? (this.actividadProtegida() ?? []) : (panel?.actividad ?? []);
    return lista.map(describir);
  });

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set('');
    this.http.get<PanelAdmin>(`${environment.apiUrl}/instituciones/panel`).subscribe({
      next: (datos) => {
        this.panel.set(datos);
        this.cargando.set(false);
        this.cargarActividadProtegida();
      },
      error: () => {
        this.error.set('No se pudo cargar el panel. Verificá que el servidor esté en línea.');
        this.cargando.set(false);
      },
    });
  }

  private cargarActividadProtegida(): void {
    const clave = this.bitacoraClave.clave();
    if (!this.panel()?.bitacora_protegida || !clave) return;
    this.bitacora.listar(clave, {}, { limite: 8, sinAccesos: true }).subscribe({
      next: (logs) =>
        this.actividadProtegida.set(
          logs.map((l) => ({
            fecha: l.fecha,
            usuario: l.usuario_correo,
            modulo: l.modulo,
            accion: l.accion,
            detalles: l.detalles,
            resultado: l.resultado,
          })),
        ),
      error: () => this.actividadProtegida.set([]),
    });
  }
}
