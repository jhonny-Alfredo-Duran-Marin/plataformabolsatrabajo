import { Component, inject, OnInit } from '@angular/core';
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
  
  isLoading = true;
  savingStatus: 'idle' | 'saving' | 'saved' | 'error' = 'idle';
  
  visibilidad: VisibilidadData = {
    perfil_oculto: false,
    secciones_visibles: {
      datos_contacto: true,
      experiencia_laboral: true,
      formacion_adicional: true,
      idiomas: true,
      certificaciones: true,
      habilidades: true
    }
  };

  ngOnInit() {
    this.cargarConfiguracion();
  }

  private getHeaders() {
    // Aquí normalmente iría el token de un servicio de autenticación
    // Por ahora usamos localStorage simulado
    const token = localStorage.getItem('token');
    return new HttpHeaders({
      'Authorization': `Bearer ${token}`
    });
  }

  cargarConfiguracion() {
    this.http.get<any>(`${environment.apiUrl}/perfiles/me`, { headers: this.getHeaders() })
      .subscribe({
        next: (perfil) => {
          this.visibilidad.perfil_oculto = perfil.perfil_oculto || false;
          if (perfil.visibilidad_secciones) {
            try {
              // El backend devuelve un string JSON (Text en DB)
              const parsed = typeof perfil.visibilidad_secciones === 'string' 
                ? JSON.parse(perfil.visibilidad_secciones) 
                : perfil.visibilidad_secciones;
              this.visibilidad.secciones_visibles = { ...this.visibilidad.secciones_visibles, ...parsed };
            } catch (e) {}
          }
          this.isLoading = false;
        },
        error: (err) => {
          console.error('Error cargando perfil', err);
          // Permitimos que cargue la interfaz de todas formas para demostración
          this.isLoading = false; 
        }
      });
  }

  toggleGlobal() {
    this.visibilidad.perfil_oculto = !this.visibilidad.perfil_oculto;
    this.guardarCambios();
  }

  toggleSeccion(seccion: keyof VisibilidadData['secciones_visibles']) {
    this.visibilidad.secciones_visibles[seccion] = !this.visibilidad.secciones_visibles[seccion];
    this.guardarCambios();
  }

  guardarCambios() {
    this.savingStatus = 'saving';
    
    // Convertimos la data al formato del backend
    const payload = {
      perfil_oculto: this.visibilidad.perfil_oculto,
      secciones_visibles: this.visibilidad.secciones_visibles
    };

    this.http.patch(`${environment.apiUrl}/perfiles/me/visibilidad`, payload, { headers: this.getHeaders() })
      .subscribe({
        next: () => {
          this.savingStatus = 'saved';
          setTimeout(() => this.savingStatus = 'idle', 2000);
        },
        error: (err) => {
          console.error('Error al guardar', err);
          this.savingStatus = 'error';
        }
      });
  }
}
