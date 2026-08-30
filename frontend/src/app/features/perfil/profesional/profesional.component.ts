import { CommonModule } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { environment } from '../../../../environments/environment';

interface Perfil {
  porcentaje_completitud: number;
  disponibilidad: string | null;
  carrera_id: string | null;
  anio_egreso: number | null;
  matricula: string | null;
  titulo_profesional: string | null;
  resumen_profesional: string | null;
}

interface Formacion {
  id: string;
  institucion: string;
  programa: string;
  estado_academico: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
}

interface Experiencia {
  id: string;
  empresa: string;
  cargo: string;
  descripcion: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
}

interface Idioma {
  id: string;
  idioma: string;
  nivel: string;
}

interface Certificacion {
  id: string;
  nombre: string;
  entidad_emisora: string | null;
  fecha_obtencion: string | null;
}

interface Habilidad {
  id: string;
  nombre: string;
  categoria: string | null;
}

@Component({
  selector: 'app-perfil-profesional',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './profesional.component.html',
  styleUrl: './profesional.component.scss',
})
export class ProfesionalComponent implements OnInit {
  private http = inject(HttpClient);
  private readonly apiBase = `${environment.apiUrl}/perfiles/me`;

  readonly perfil = signal<Perfil | null>(null);
  readonly formaciones = signal<Formacion[]>([]);
  readonly experiencias = signal<Experiencia[]>([]);
  readonly idiomas = signal<Idioma[]>([]);
  readonly certificaciones = signal<Certificacion[]>([]);
  readonly habilidades = signal<Habilidad[]>([]);

  readonly cargando = signal(true);
  readonly guardando = signal(false);

  disponibilidadOpciones = [
    { valor: 'inmediata', etiqueta: 'Inmediata' },
    { valor: '1_semana', etiqueta: '1 semana' },
    { valor: '2_semanas', etiqueta: '2 semanas' },
    { valor: '1_mes', etiqueta: '1 mes' },
  ];

  nuevaFormacion: Partial<Formacion> = {};
  nuevaExperiencia: Partial<Experiencia> = {};
  nuevoIdioma: Partial<Idioma> = { nivel: 'basico' };
  nuevaCertificacion: Partial<Certificacion> = {};
  habilidadTexto = '';

  ngOnInit(): void {
    this.cargarTodo();
  }

  private headers(): HttpHeaders {
    const token = localStorage.getItem('token');
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  cargarTodo(): void {
    this.cargando.set(true);
    this.http.get<Perfil>(this.apiBase, { headers: this.headers() }).subscribe({
      next: (perfil) => {
        this.perfil.set(perfil);
        this.cargando.set(false);
      },
      error: () => this.cargando.set(false),
    });
    this.http
      .get<Formacion[]>(`${this.apiBase}/formacion`, { headers: this.headers() })
      .subscribe((r) => this.formaciones.set(r));
    this.http
      .get<Experiencia[]>(`${this.apiBase}/experiencia`, { headers: this.headers() })
      .subscribe((r) => this.experiencias.set(r));
    this.http
      .get<Idioma[]>(`${this.apiBase}/idiomas`, { headers: this.headers() })
      .subscribe((r) => this.idiomas.set(r));
    this.http
      .get<Certificacion[]>(`${this.apiBase}/certificaciones`, { headers: this.headers() })
      .subscribe((r) => this.certificaciones.set(r));
    this.http
      .get<Habilidad[]>(`${this.apiBase}/habilidades`, { headers: this.headers() })
      .subscribe((r) => this.habilidades.set(r));
  }

  private refrescarPerfil(): void {
    this.http
      .get<Perfil>(this.apiBase, { headers: this.headers() })
      .subscribe((perfil) => this.perfil.set(perfil));
  }

  actualizarPerfil(cambios: Partial<Perfil>): void {
    this.perfil.update((actual) => (actual ? { ...actual, ...cambios } : actual));
  }

  guardarDatosBasicos(): void {
    const actual = this.perfil();
    if (!actual) return;
    this.guardando.set(true);
    this.http
      .patch(
        this.apiBase,
        {
          disponibilidad: actual.disponibilidad,
          titulo_profesional: actual.titulo_profesional,
          resumen_profesional: actual.resumen_profesional,
        },
        { headers: this.headers() },
      )
      .subscribe({
        next: () => {
          this.guardando.set(false);
          this.refrescarPerfil();
        },
        error: () => this.guardando.set(false),
      });
  }

  agregarFormacion(): void {
    if (!this.nuevaFormacion.institucion || !this.nuevaFormacion.programa) return;
    this.http.post<Formacion>(`${this.apiBase}/formacion`, this.nuevaFormacion, { headers: this.headers() }).subscribe(() => {
      this.nuevaFormacion = {};
      this.cargarTodo();
    });
  }

  eliminarFormacion(id: string): void {
    this.http.delete(`${this.apiBase}/formacion/${id}`, { headers: this.headers() }).subscribe(() => this.cargarTodo());
  }

  agregarExperiencia(): void {
    if (!this.nuevaExperiencia.empresa || !this.nuevaExperiencia.cargo) return;
    this.http
      .post<Experiencia>(`${this.apiBase}/experiencia`, this.nuevaExperiencia, { headers: this.headers() })
      .subscribe(() => {
        this.nuevaExperiencia = {};
        this.cargarTodo();
      });
  }

  eliminarExperiencia(id: string): void {
    this.http.delete(`${this.apiBase}/experiencia/${id}`, { headers: this.headers() }).subscribe(() => this.cargarTodo());
  }

  agregarIdioma(): void {
    if (!this.nuevoIdioma.idioma) return;
    this.http.post<Idioma>(`${this.apiBase}/idiomas`, this.nuevoIdioma, { headers: this.headers() }).subscribe(() => {
      this.nuevoIdioma = { nivel: 'basico' };
      this.cargarTodo();
    });
  }

  eliminarIdioma(id: string): void {
    this.http.delete(`${this.apiBase}/idiomas/${id}`, { headers: this.headers() }).subscribe(() => this.cargarTodo());
  }

  agregarCertificacion(): void {
    if (!this.nuevaCertificacion.nombre) return;
    this.http
      .post<Certificacion>(`${this.apiBase}/certificaciones`, this.nuevaCertificacion, { headers: this.headers() })
      .subscribe(() => {
        this.nuevaCertificacion = {};
        this.cargarTodo();
      });
  }

  eliminarCertificacion(id: string): void {
    this.http.delete(`${this.apiBase}/certificaciones/${id}`, { headers: this.headers() }).subscribe(() => this.cargarTodo());
  }

  agregarHabilidad(): void {
    const nombre = this.habilidadTexto.trim();
    if (!nombre) return;
    const nombres = [...this.habilidades().map((h) => h.nombre), nombre];
    this.http.put<Habilidad[]>(`${this.apiBase}/habilidades`, { habilidades: nombres }, { headers: this.headers() }).subscribe(() => {
      this.habilidadTexto = '';
      this.cargarTodo();
    });
  }

  eliminarHabilidad(nombre: string): void {
    const nombres = this.habilidades()
      .map((h) => h.nombre)
      .filter((n) => n !== nombre);
    this.http.put<Habilidad[]>(`${this.apiBase}/habilidades`, { habilidades: nombres }, { headers: this.headers() }).subscribe(() => {
      this.cargarTodo();
    });
  }

  descargarCv(): void {
    this.http.get(`${this.apiBase}/cv`, { headers: this.headers(), responseType: 'blob', observe: 'response' }).subscribe({
      next: (respuesta) => {
        const disposicion = respuesta.headers.get('content-disposition') || '';
        const coincidencia = /filename=([^;]+)/.exec(disposicion);
        const nombreArchivo = coincidencia ? coincidencia[1].trim() : 'CV.pdf';
        const blob = respuesta.body as Blob;
        const url = window.URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = nombreArchivo;
        enlace.click();
        window.URL.revokeObjectURL(url);
      },
    });
  }
}
