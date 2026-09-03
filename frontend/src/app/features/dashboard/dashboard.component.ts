import { ChangeDetectorRef, Component, OnInit, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { VacanteService } from '../../core/services/vacante.service';

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

  role = computed(() => this.auth.rol() || '—');
  isAdmin = computed(() => this.auth.rol() === 'platform_admin' || this.auth.rol() === 'moderator');
  isEgresado = computed(() => this.auth.rol() === 'candidate');
  isEmpresa = computed(() => this.auth.rol() === 'empresa');

  vacantesPublicadas = 0;
  vacantesEnRevision = 0;

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
  }
}
