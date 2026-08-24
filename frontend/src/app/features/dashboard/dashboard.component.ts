import { Component, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent {
  auth = inject(AuthService);

  role    = computed(() => this.auth.userRole() ?? '—');
  isAdmin  = computed(() => this.auth.userRole() === 'ADMINISTRADOR');
  isEgresado = computed(() => this.auth.userRole() === 'EGRESADO' || this.auth.userRole() === 'ESTUDIANTE');
  isEmpresa  = computed(() => this.auth.userRole() === 'EMPRESA');
}
