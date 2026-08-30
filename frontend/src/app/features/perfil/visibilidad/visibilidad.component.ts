import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

interface VisibilidadData {
  perfil_oculto: boolean;
  secciones_visibles: {
    datos_contacto: boolean;
    experiencia_laboral: boolean;
    formacion_adicional: boolean;
    idiomas: boolean;
    certificaciones: boolean;
    habilidades: boolean;
  };
}

@Component({
  selector: 'app-visibilidad',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './visibilidad.component.html',
  styleUrl: './visibilidad.component.scss'
})
export class VisibilidadComponent implements OnInit {
  private http = inject(HttpClient);

  readonly isLoading = signal(true);
  readonly savingStatus = signal<'idle' | 'saving' | 'saved' | 'error'>('idle');

  readonly visibilidad = signal<VisibilidadData>({
    perfil_oculto: false,
    secciones_visibles: {
      datos_contacto: true,
      experiencia_laboral: true,
      formacion_adicional: true,
      idiomas: true,
      certificaciones: true,
      habilidades: true
    }
  });

  ngOnInit() {
    this.cargarConfiguracion();
  }

  private getHeaders() {
    const token = localStorage.getItem('token');
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
  }

  cargarConfiguracion() {
    this.http.get<any>(`${environment.apiUrl}/perfiles/me`, { headers: this.getHeaders() })
      .subscribe({
        next: (perfil) => {
          const actual = this.visibilidad();
          let secciones = actual.secciones_visibles;
          if (perfil.visibilidad_secciones) {
            try {
              const parsed = typeof perfil.visibilidad_secciones === 'string'
                ? JSON.parse(perfil.visibilidad_secciones)
                : perfil.visibilidad_secciones;
              secciones = { ...secciones, ...parsed };
            } catch (e) {
              /* se mantiene el valor por defecto si el JSON es invalido */
            }
          }
          this.visibilidad.set({
            perfil_oculto: perfil.perfil_oculto || false,
            secciones_visibles: secciones,
          });
          this.isLoading.set(false);
        },
        error: (err) => {
          console.error('Error cargando perfil', err);
          this.isLoading.set(false);
        }
      });
  }

  toggleGlobal() {
    this.visibilidad.update((actual) => ({ ...actual, perfil_oculto: !actual.perfil_oculto }));
    this.guardarCambios();
  }

  toggleSeccion(seccion: keyof VisibilidadData['secciones_visibles']) {
    this.visibilidad.update((actual) => ({
      ...actual,
      secciones_visibles: {
        ...actual.secciones_visibles,
        [seccion]: !actual.secciones_visibles[seccion],
      },
    }));
    this.guardarCambios();
  }

  guardarCambios() {
    this.savingStatus.set('saving');

    const payload = {
      perfil_oculto: this.visibilidad().perfil_oculto,
      secciones_visibles: this.visibilidad().secciones_visibles
    };

    this.http.patch(`${environment.apiUrl}/perfiles/me/visibilidad`, payload, { headers: this.getHeaders() })
      .subscribe({
        next: () => {
          this.savingStatus.set('saved');
          setTimeout(() => this.savingStatus.set('idle'), 2000);
        },
        error: (err) => {
          console.error('Error al guardar', err);
          this.savingStatus.set('error');
        }
      });
  }
}
