import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  EstadisticasPublicas,
  FiltrosBusquedaVacantes,
  FiltrosDisponibles,
  VacanteDetalle,
  VacanteResumen,
} from '../../../core/models/vacante.models';
import { VacanteService } from '../../../core/services/vacante.service';
import { AuthService } from '../../auth/auth.service';
import { DenunciarOfertaComponent } from '../../moderacion/denunciar-oferta/denunciar-oferta.component';
import { PostulacionModalComponent } from '../../../shared/components/postulacion-modal/postulacion-modal.component';
import { NotificacionesCampanaComponent } from '../../../shared/components/notificaciones-campana/notificaciones-campana.component';

@Component({
  selector: 'app-busqueda-vacantes',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    PostulacionModalComponent,
    NotificacionesCampanaComponent,
    DenunciarOfertaComponent,
  ],
  templateUrl: './busqueda-vacantes.component.html',
  styleUrl: './busqueda-vacantes.component.scss',
})
export class BusquedaVacantesComponent implements OnInit {
  private readonly vacanteService = inject(VacanteService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);
  readonly auth = inject(AuthService);

  // Estadísticas públicas agregadas (HU-34)
  readonly stats = signal<EstadisticasPublicas | null>(null);
  readonly isLoadingStats = signal(false);

  // Estados de datos
  readonly vacantes = signal<VacanteResumen[]>([]);
  filtrosDisponibles: FiltrosDisponibles | null = null;
  readonly totalVacantes = signal(0);
  readonly isLoading = signal(false);
  readonly errorMessage = signal<string | null>(null);

  // Filtros aplicados
  filtroTexto = '';
  filtroModalidad = '';
  filtroJornada = '';
  filtroCiudad = '';
  filtroCarreraId = '';
  filtroCategoriaId = '';
  filtroSeniority = '';
  filtroSalarioMin: number | null = null;
  filtroSalarioMax: number | null = null;
  filtroOrdenarPor: 'fecha' | 'afinidad' = 'fecha';

  // HU-25: Búsqueda Semántica con IA
  modoSemantico = false;
  sugerenciaSemantica: string | null = null;
  iaDisponible = true;

  alternarModoSemantico(): void {
    this.modoSemantico = !this.modoSemantico;
    this.sugerenciaSemantica = null;
    this.ejecutarBusqueda();
  }

  // Modal de detalle de vacante
  vacanteSeleccionada: VacanteDetalle | null = null;
  readonly isLoadingDetalle = signal(false);
  showModalDetalle = false;

  // Postulación feedback
  toastMessage: string | null = null;
  mostrarModalPostulacion = false;

  ngOnInit(): void {
    // Las estadísticas son de toda la plataforma; el egresado solo ve las vacantes de su
    // universidad, así que para él la franja mostraría un total que no coincide con su listado.
    if (this.auth.rol() !== 'candidate') {
      this.cargarEstadisticas();
    }
    this.cargarFiltrosDisponibles();
    this.ejecutarBusqueda();
  }

  cargarEstadisticas(): void {
    this.isLoadingStats.set(true);
    this.vacanteService.obtenerEstadisticasPublicas().subscribe({
      next: (data) => {
        this.stats.set(data);
        this.isLoadingStats.set(false);
      },
      error: (err) => {
        console.error('Error al cargar estadísticas públicas', err);
        this.isLoadingStats.set(false);
      },
    });
  }

  cargarFiltrosDisponibles(): void {
    this.vacanteService.obtenerFiltrosDisponibles().subscribe({
      next: (data) => {
        this.filtrosDisponibles = data;
      },
      error: (err) => {
        console.error('Error al cargar filtros disponibles', err);
      },
    });
  }

  ejecutarBusqueda(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.cdr.markForCheck();

    if (this.modoSemantico) {
      this.vacanteService.busquedaSemantica(this.filtroTexto || 'vacantes vigentes', {
        ciudad: this.filtroCiudad || undefined,
        modalidad: this.filtroModalidad || undefined,
        carrera_id: this.filtroCarreraId || undefined,
        salario_min: this.filtroSalarioMin !== null ? this.filtroSalarioMin : undefined,
        seniority: this.filtroSeniority || undefined,
      }).subscribe({
        next: (resp) => {
          this.sugerenciaSemantica = resp.sugerencia;
          this.iaDisponible = resp.ia_disponible;
          const transformados: VacanteResumen[] = (resp.items || []).map((it: any) => ({
            id: it.id,
            company: {
              id: it.id,
              legal_name: it.company_name,
              trade_name: it.company_name,
              city: it.city,
            },
            title: it.title,
            description: it.description,
            seniority_level: it.seniority_level,
            employment_type: it.employment_type,
            work_modality: it.work_modality,
            country_code: 'BO',
            city: it.city,
            salary_min: it.salary_min,
            salary_max: it.salary_max,
            currency: it.currency || 'BOB',
            salary_visible: true,
            positions_available: 1,
            status: 'published',
            published_at: it.published_at,
            view_count: 0,
            skills: [],
            education_preferences: [],
            score_relevancia: it.score_relevancia,
            razon_coincidencia: it.razon_coincidencia,
          }));
          this.vacantes.set(transformados);
          this.totalVacantes.set(resp.total);
          this.isLoading.set(false);
          this.cdr.markForCheck();
        },
        error: () => {
          this.isLoading.set(false);
          this.errorMessage.set('Error en la búsqueda semántica. Intenta nuevamente.');
          this.cdr.markForCheck();
        },
      });
      return;
    }

    const filtros: FiltrosBusquedaVacantes = {
      q: this.filtroTexto,
      modalidad: this.filtroModalidad || undefined,
      jornada: this.filtroJornada || undefined,
      ciudad: this.filtroCiudad || undefined,
      carrera_id: this.filtroCarreraId || undefined,
      categoria_id: this.filtroCategoriaId || undefined,
      seniority: this.filtroSeniority || undefined,
      salario_min: this.filtroSalarioMin !== null ? this.filtroSalarioMin : undefined,
      salario_max: this.filtroSalarioMax !== null ? this.filtroSalarioMax : undefined,
      ordenar_por: this.filtroOrdenarPor,
      limit: 50,
      offset: 0,
    };

    this.vacanteService.buscarVacantes(filtros).subscribe({
      next: (resp) => {
        this.vacantes.set(resp.items);
        this.totalVacantes.set(resp.total);
        this.isLoading.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoading.set(false);
        this.errorMessage.set('No se pudieron cargar las ofertas de empleo. Intenta nuevamente.');
        this.cdr.markForCheck();
      },
    });
  }

  limpiarFiltros(): void {
    this.filtroTexto = '';
    this.filtroModalidad = '';
    this.filtroJornada = '';
    this.filtroCiudad = '';
    this.filtroCarreraId = '';
    this.filtroCategoriaId = '';
    this.filtroSeniority = '';
    this.filtroSalarioMin = null;
    this.filtroSalarioMax = null;
    this.filtroOrdenarPor = 'fecha';
    this.ejecutarBusqueda();
  }

  tieneFiltrosActivos(): boolean {
    return Boolean(
      this.filtroTexto ||
      this.filtroModalidad ||
      this.filtroJornada ||
      this.filtroCiudad ||
      this.filtroCarreraId ||
      this.filtroCategoriaId ||
      this.filtroSeniority ||
      this.filtroSalarioMin !== null ||
      this.filtroSalarioMax !== null,
    );
  }

  verDetalle(vacanteId: string): void {
    this.isLoadingDetalle.set(true);
    this.showModalDetalle = true;
    this.vacanteSeleccionada = null;
    this.cdr.markForCheck();

    this.vacanteService.obtenerDetalle(vacanteId).subscribe({
      next: (detalle) => {
        this.vacanteSeleccionada = detalle;
        this.isLoadingDetalle.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoadingDetalle.set(false);
        this.cdr.markForCheck();
        this.mostrarToast('No se pudo cargar el detalle de la vacante.', true);
        this.cerrarModalDetalle();
      },
    });
  }

  get estaAutenticado(): boolean {
    const token = this.auth.token();
    if (!token) return false;
    try {
      // Decodificar el payload del JWT (parte central entre los dos puntos)
      const payload = JSON.parse(atob(token.split('.')[1]));
      const ahora = Math.floor(Date.now() / 1000);
      if (payload.exp && payload.exp < ahora) {
        // Token expirado: limpiar sesión y devolver false
        this.auth.cerrarSesion();
        return false;
      }
      return true;
    } catch {
      // Token malformado: tratar como no autenticado
      return false;
    }
  }

  cerrarModalDetalle(): void {
    this.showModalDetalle = false;
    this.vacanteSeleccionada = null;
  }

  irARegistro(vacanteId?: string): void {
    const id = vacanteId || this.vacanteSeleccionada?.id;
    const returnUrl = id ? `/vacantes/${id}` : '/vacantes';
    this.cerrarModalDetalle();
    void this.router.navigate(['/auth/registro'], { queryParams: { returnUrl } });
  }

  postularse(): void {
    if (!this.estaAutenticado) {
      this.irARegistro(this.vacanteSeleccionada?.id);
      return;
    }
    this.mostrarModalPostulacion = true;
  }

  cerrarModalPostulacion(): void {
    this.mostrarModalPostulacion = false;
  }

  onPostulacionExitosa(): void {
    this.mostrarModalPostulacion = false;
    this.cerrarModalDetalle();
    this.mostrarToast('¡Postulación enviada exitosamente! La empresa revisará tu perfil.');
  }

  getModalidadLabel(mod: string): string {
    switch (mod) {
      case 'on_site':
      case 'onsite':
        return 'Presencial';
      case 'remote':
        return 'Remoto';
      case 'hybrid':
        return 'Híbrido';
      default:
        return mod;
    }
  }

  getJornadaLabel(jornada: string): string {
    switch (jornada) {
      case 'full_time':
      case 'permanent':
        return 'Tiempo Completo';
      case 'part_time':
        return 'Medio Tiempo';
      case 'internship':
        return 'Pasantía';
      case 'temporary':
        return 'Temporal';
      case 'contract':
      case 'contractor':
        return 'Por Contrato';
      case 'freelance':
        return 'Freelance / Consultoría';
      default:
        return jornada;
    }
  }

  getSeniorityLabel(seniority: string): string {
    switch (seniority) {
      case 'internship':
        return 'Pasantía';
      case 'junior':
        return 'Junior';
      case 'mid':
        return 'Intermedio';
      case 'senior':
        return 'Senior';
      case 'lead':
        return 'Líder / Supervisor';
      default:
        return seniority;
    }
  }

  mostrarToast(mensaje: string, isError = false): void {
    this.toastMessage = mensaje;
    setTimeout(() => {
      if (this.toastMessage === mensaje) {
        this.toastMessage = null;
      }
    }, 4000);
  }
}
