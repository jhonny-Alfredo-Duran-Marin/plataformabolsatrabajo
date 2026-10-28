import { ChangeDetectorRef, Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../auth/auth.service';
import { VacanteService } from '../../core/services/vacante.service';
import { environment } from '../../../environments/environment';
import { PostulacionService, PostulacionListResponse } from '../../core/services/postulacion.service';
import { SeleccionService } from '../seleccion/seleccion.service';
import { IaService } from '../ia/ia.service';

import { NotificacionesCampanaComponent } from '../../shared/components/notificaciones-campana/notificaciones-campana.component';

interface InstitucionEmpresa {
  id: string;
  nombre: string;
  sigla: string | null;
  estado: 'pending' | 'approved' | 'rejected' | 'suspended' | null;
  motivo_rechazo: string | null;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, NotificacionesCampanaComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  auth = inject(AuthService);
  readonly ia = inject(IaService);
  private readonly vacanteService = inject(VacanteService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly http = inject(HttpClient);
  private readonly postulacionService = inject(PostulacionService);
  private readonly seleccionService = inject(SeleccionService);

  role = computed(() => this.auth.rol() || '—');
  isAdmin = computed(() => this.auth.rol() === 'platform_admin' || this.auth.rol() === 'moderator');
  isEgresado = computed(() => this.auth.rol() === 'candidate');
  isEmpresa = computed(() => this.auth.rol() === 'empresa');

  vacantesPublicadas = 0;
  vacantesEnRevision = 0;
  postulantesRecibidos = 0;
  postulantesEnProceso = 0;

  institucionesEmpresa = signal<InstitucionEmpresa[]>([]);
  solicitando = signal<string | null>(null);
  readonly etiquetaEstado: Record<string, string> = {
    pending: 'Pendiente',
    approved: 'Aprobada',
    rejected: 'Rechazada',
    suspended: 'Suspendida',
  };

  perfilPorcentaje = signal<number>(0);
  postulaciones = signal<PostulacionListResponse[]>([]);
  postulacionesActivasCount = computed(() =>
    this.postulaciones().filter((p) => p.current_status !== 'withdrawn' && p.current_status !== 'rejected').length,
  );

  ngOnInit(): void {
    if (this.isEmpresa()) {
      this.vacanteService.listarMisVacantes({ estado: 'published', page: 1, page_size: 1 }).subscribe({
        next: (data) => {
          this.vacantesPublicadas = data.total;
          this.cdr.markForCheck();
        },
      });
      this.vacanteService.listarMisVacantes({ estado: 'pending_review', page: 1, page_size: 1 }).subscribe({
        next: (data) => {
          this.vacantesEnRevision = data.total;
          this.cdr.markForCheck();
        },
      });
      this.seleccionService.listarVacantes().subscribe({
        next: (vacantes) => {
          this.postulantesRecibidos = vacantes.reduce((acc, v) => acc + v.total_postulantes, 0);
          this.postulantesEnProceso = vacantes.reduce((acc, v) => acc + v.total_activos, 0);
          this.cdr.markForCheck();
        },
        error: () => console.error('Error cargando metricas de seleccion en dashboard'),
      });
      this.http.get<InstitucionEmpresa[]>(`${environment.apiUrl}/instituciones/empresa`).subscribe({
        next: (data) => this.institucionesEmpresa.set(data),
      });
    }

    if (this.isEgresado()) {
      this.http.get<any>(`${environment.apiUrl}/perfiles/me`).subscribe({
        next: (data) => this.perfilPorcentaje.set(data.porcentaje_completitud || 0),
        error: () => console.error('Error cargando perfil en dashboard'),
      });

      this.postulacionService.getMisPostulaciones().subscribe({
        next: (data) => this.postulaciones.set(data),
        error: () => console.error('Error cargando postulaciones en dashboard'),
      });
    }
  }

  solicitarAcceso(institucionId: string): void {
    this.solicitando.set(institucionId);
    this.http
      .post<InstitucionEmpresa>(`${environment.apiUrl}/instituciones/empresa/${institucionId}/solicitar`, {})
      .subscribe({
        next: (actualizada) => {
          this.institucionesEmpresa.update((lista) => lista.map((u) => (u.id === actualizada.id ? actualizada : u)));
          this.solicitando.set(null);
        },
        error: () => this.solicitando.set(null),
      });
  }
}
