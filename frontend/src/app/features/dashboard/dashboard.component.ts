import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../auth/auth.service';
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
  http = inject(HttpClient);
  postulacionService = inject(PostulacionService);

  // Para poder compilar si `rol` no existe como signal (asumiendo que en tu versin es getUserRole o similar)
  role = computed(() => {
    try {
      return (this.auth as any).rol?.() || (this.auth as any).userRole?.() || '—';
    } catch { return '—'; }
  });
  isAdmin = computed(() => this.role() === 'platform_admin' || this.role() === 'moderator' || this.role() === 'ADMINISTRADOR');
  isEgresado = computed(() => this.role() === 'candidate' || this.role() === 'EGRESADO');
  isEmpresa = computed(() => this.role() === 'empresa' || this.role() === 'EMPRESA');


 // ID falso para visualizar
  
  perfilPorcentaje = signal<number>(0);
  postulaciones = signal<PostulacionListResponse[]>([]);
  postulacionesActivasCount = computed(() => this.postulaciones().filter(p => p.current_status !== 'withdrawn' && p.current_status !== 'rejected').length);

  ngOnInit() {
    if (this.isEgresado()) {
      this.http.get<any>(`${environment.apiUrl}/perfiles/me`).subscribe({
        next: (data) => this.perfilPorcentaje.set(data.porcentaje_completitud || 0),
        error: () => console.error('Error cargando perfil en dashboard')
      });
      
      this.postulacionService.getMisPostulaciones().subscribe({
        next: (data) => this.postulaciones.set(data),
        error: () => console.error('Error cargando postulaciones en dashboard')
      });
    }
  }
}
