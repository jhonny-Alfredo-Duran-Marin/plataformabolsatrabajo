import { Component, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService } from '../auth/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent {
  auth = inject(AuthService);

  role = computed(() => this.auth.rol() || '—');
  isAdmin = computed(() => this.auth.rol() === 'platform_admin' || this.auth.rol() === 'moderator');
  isEgresado = computed(() => this.auth.rol() === 'candidate');
  isEmpresa = computed(() => this.auth.rol() === 'empresa');
}
