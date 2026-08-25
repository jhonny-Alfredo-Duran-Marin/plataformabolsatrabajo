import { Component, inject, OnInit, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

import { environment } from '../../../../environments/environment';
import { AuthService } from '../../auth/auth.service';

interface Estadistica {
  etiqueta: string;
  valor: number;
  detalle: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  readonly saludo = this.auth.correo() || 'Administrador';
  readonly estadisticas = signal<Estadistica[]>([]);
  readonly ultimasAcciones = signal<{ fecha: string; accion: string; detalles: string | null }[]>([]);
  readonly cargando = signal(true);
  readonly error = signal('');

  ngOnInit(): void {
    const headers = new HttpHeaders({ Authorization: `Bearer ${this.auth.token()}` });
    const base = environment.apiUrl;

    const usuarios$ = this.http.get<any[]>(`${base}/admin/usuarios`, { headers });
    const pendientesEg$ = this.http.get<any[]>(`${base}/validacion/egresados/pendientes`, { headers });
    const pendientesEmp$ = this.http.get<any[]>(`${base}/validacion/empresas/pendientes`, { headers });
    const bitacora$ = this.http.get<any[]>(`${base}/bitacora`, { headers });

    this.cargando.set(true);
    usuarios$.subscribe({
      next: (usuarios) => {
        const candidatos = usuarios.filter((u) => u.roles.includes('candidate')).length;
        const moderadores = usuarios.filter((u) => u.roles.includes('moderator')).length;
        const empresas = usuarios.filter((u) => u.es_miembro_empresa).length;
        this.estadisticas.set([
          { etiqueta: 'Usuarios totales', valor: usuarios.length, detalle: 'cuentas activas en el sistema' },
          { etiqueta: 'Egresados', valor: candidatos, detalle: 'con rol de candidato' },
          { etiqueta: 'Empresas', valor: empresas, detalle: 'miembros de empresa registradas' },
          { etiqueta: 'Moderadores', valor: moderadores + 1, detalle: '+ administrador universitario' },
        ]);
      },
      error: () => this.error.set('No se pudieron cargar las estadísticas de usuarios.'),
    });

    let egresadosPendientes = 0;
    let empresasPendientes = 0;
    pendientesEg$.subscribe({
      next: (lista) => (egresadosPendientes = lista.length),
      error: () => {},
    });
    pendientesEmp$.subscribe({
      next: (lista) => (empresasPendientes = lista.length),
      complete: () =>
        this.estadisticas.update((stats) => [
          ...stats,
          {
            etiqueta: 'Validaciones pendientes',
            valor: egresadosPendientes + empresasPendientes,
            detalle: `${egresadosPendientes} egresados · ${empresasPendientes} empresas`,
          },
        ]),
    });

    bitacora$.subscribe({
      next: (logs) => {
        this.ultimasAcciones.set(
          logs.slice(0, 6).map((l) => ({
            fecha: new Date(l.fecha).toLocaleString(),
            accion: l.accion,
            detalles: l.detalles ?? `${l.modulo}`,
          })),
        );
        this.cargando.set(false);
      },
      error: () => {
        this.cargando.set(false);
      },
    });
  }
}
