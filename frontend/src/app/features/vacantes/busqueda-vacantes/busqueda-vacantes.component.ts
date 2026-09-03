import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  FiltrosBusquedaVacantes,
  FiltrosDisponibles,
  VacanteDetalle,
  VacanteResumen,
} from '../../../core/models/vacante.models';
import { VacanteService } from '../../../core/services/vacante.service';
import { AuthService } from '../../auth/auth.service';

@Component({
  selector: 'app-busqueda-vacantes',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './busqueda-vacantes.component.html',
  styleUrl: './busqueda-vacantes.component.scss',
})
export class BusquedaVacantesComponent implements OnInit {
  private readonly vacanteService = inject(VacanteService);
  readonly auth = inject(AuthService);

  // Estados de datos
  vacantes: VacanteResumen[] = [];
  filtrosDisponibles: FiltrosDisponibles | null = null;
  totalVacantes = 0;
  isLoading = false;
  errorMessage: string | null = null;

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

  // Modal de detalle de vacante
  vacanteSeleccionada: VacanteDetalle | null = null;
  isLoadingDetalle = false;
  showModalDetalle = false;

  // Postulación feedback
  toastMessage: string | null = null;

  ngOnInit(): void {
    this.cargarFiltrosDisponibles();
    this.ejecutarBusqueda();
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
    this.isLoading = true;
    this.errorMessage = null;

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
        this.vacantes = resp.items;
        this.totalVacantes = resp.total;
        this.isLoading = false;
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = 'No se pudieron cargar las ofertas de empleo. Intenta nuevamente.';
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
      this.filtroSalarioMax !== null
    );
  }

  verDetalle(vacanteId: string): void {
    this.isLoadingDetalle = true;
    this.showModalDetalle = true;
    this.vacanteSeleccionada = null;

    this.vacanteService.obtenerDetalle(vacanteId).subscribe({
      next: (detalle) => {
        this.vacanteSeleccionada = detalle;
        this.isLoadingDetalle = false;
      },
      error: () => {
        this.isLoadingDetalle = false;
        this.mostrarToast('No se pudo cargar el detalle de la vacante.', true);
        this.cerrarModalDetalle();
      },
    });
  }

  cerrarModalDetalle(): void {
    this.showModalDetalle = false;
    this.vacanteSeleccionada = null;
  }

  postularse(): void {
    if (!this.auth.estaAutenticado()) {
      this.mostrarToast('Debes iniciar sesión como egresado para postularte.', true);
      return;
    }
    this.mostrarToast('¡Postulación enviada exitosamente! La empresa revisará tu perfil.');
    this.cerrarModalDetalle();
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
      case 'contractor':
        return 'Por Contrato';
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

