import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Vacante } from '../../../core/models/vacante.models';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { VacanteService } from '../../../core/services/vacante.service';

/**
 * Componente para visualizar el detalle completo de una vacante laboral.
 */
@Component({
  selector: 'app-vacante-detalle',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './vacante-detalle.component.html',
  styleUrl: './vacante-detalle.component.scss',
})
export class VacanteDetalleComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly vacanteService = inject(VacanteService);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);

  vacante: Vacante | null = null;
  cargando = true;
  errorMsg: string | null = null;

  get userRole(): string | null {
    return this.auth.getUserRole();
  }

  get isEmpresa(): boolean {
    return this.userRole === 'EMPRESA';
  }

  get isCandidato(): boolean {
    return this.userRole === 'EGRESADO' || this.userRole === 'ESTUDIANTE';
  }

  get isAdmin(): boolean {
    return this.userRole === 'ADMINISTRADOR';
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.errorMsg = 'Identificador de vacante no válido.';
      this.cargando = false;
      return;
    }
    this.cargarDetalle(id);
  }

  cargarDetalle(id: string): void {
    this.cargando = true;
    this.errorMsg = null;

    this.vacanteService.obtenerVacante(id).subscribe({
      next: (data) => {
        this.vacante = data;
        this.cargando = false;
      },
      error: (err) => {
        this.errorMsg = err.message || 'No fue posible cargar la información de la vacante.';
        this.cargando = false;
      },
    });
  }

  postular(): void {
    this.toast.info(
      'La postulación a vacantes estará disponible próximamente en el Sprint de Postulaciones.'
    );
  }

  // ─── Helpers de Formato y Etiquetas ──────────────────────────────────────

  obtenerModalidadTexto(mod?: string | null): string {
    switch (mod) {
      case 'onsite':
        return 'Presencial';
      case 'hybrid':
        return 'Híbrido';
      case 'remote':
        return 'Remoto';
      default:
        return 'No especificada';
    }
  }

  obtenerSeniorityTexto(sen?: string | null): string {
    switch (sen) {
      case 'internship':
        return 'Pasantía / Prácticas';
      case 'junior':
        return 'Junior (0 - 2 años)';
      case 'mid':
        return 'Semi Senior / Mid';
      case 'senior':
        return 'Senior';
      case 'lead':
        return 'Líder Técnico';
      case 'manager':
        return 'Gerencia / Dirección';
      default:
        return sen || 'No especificado';
    }
  }

  obtenerTipoEmpleoTexto(emp?: string | null): string {
    switch (emp) {
      case 'permanent':
        return 'Tiempo Completo (Indefinido)';
      case 'temporary':
        return 'Temporal';
      case 'project':
        return 'Por Proyecto';
      case 'internship':
        return 'Pasantía';
      case 'freelance':
        return 'Freelance / Consultoría';
      default:
        return emp || 'No especificado';
    }
  }

  obtenerNivelEducativoTexto(edu?: string | null): string {
    switch (edu) {
      case 'technical':
        return 'Técnico Superior';
      case 'undergraduate':
        return 'Licenciatura / Ingeniería';
      case 'postgraduate':
        return 'Especialidad / Diplomado';
      case 'master':
        return 'Maestría';
      default:
        return edu || 'Sin requisito estricto';
    }
  }

  obtenerBadgeClase(estado?: string | null): string {
    switch (estado) {
      case 'published':
        return 'badge--published';
      case 'draft':
        return 'badge--draft';
      case 'paused':
        return 'badge--paused';
      case 'closed':
        return 'badge--closed';
      default:
        return 'badge--default';
    }
  }

  obtenerBadgeTexto(estado?: string | null): string {
    switch (estado) {
      case 'published':
        return 'Publicada';
      case 'draft':
        return 'Borrador';
      case 'paused':
        return 'Pausada';
      case 'closed':
        return 'Cerrada';
      default:
        return estado || 'Desconocido';
    }
  }
}
