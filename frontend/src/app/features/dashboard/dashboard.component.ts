import { ChangeDetectorRef, Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../auth/auth.service';
import { VacanteService } from '../../core/services/vacante.service';
import { environment } from '../../../environments/environment';
import { PostulacionService, PostulacionListResponse } from '../../core/services/postulacion.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  auth = inject(AuthService);
  private readonly vacanteService = inject(VacanteService);
  private readonly cdr = inject(ChangeDetectorRef);
  private readonly http = inject(HttpClient);
  private readonly postulacionService = inject(PostulacionService);

  role = computed(() => this.auth.rol() || '—');
  isAdmin = computed(() => this.auth.rol() === 'platform_admin' || this.auth.rol() === 'moderator');
  isEgresado = computed(() => this.auth.rol() === 'candidate');
  isEmpresa = computed(() => this.auth.rol() === 'empresa');

  vacantesPublicadas = 0;
  vacantesEnRevision = 0;

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
}
