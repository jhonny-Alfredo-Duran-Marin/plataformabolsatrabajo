import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../../environments/environment';
import { ToastService } from '../../../core/services/toast.service';

interface Perfil {
  nombres: string;
  apellidos: string;
  estado_validacion: 'PENDIENTE' | 'APROBADO' | 'RECHAZADO' | string;
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

/** Marca de «la carga del perfil falló» (distinta de null, que es «todavía no tiene perfil»). */
const ERROR_DE_CARGA = 'error' as const;

@Component({
  selector: 'app-perfil-profesional',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './profesional.component.html',
  styleUrl: './profesional.component.scss',
})
export class ProfesionalComponent implements OnInit {
  private http = inject(HttpClient);
  private toast = inject(ToastService);
  private readonly apiBase = `${environment.apiUrl}/perfiles/me`;

  readonly perfil = signal<Perfil | null>(null);
  readonly formaciones = signal<Formacion[]>([]);
  readonly experiencias = signal<Experiencia[]>([]);
  readonly idiomas = signal<Idioma[]>([]);
  readonly certificaciones = signal<Certificacion[]>([]);
  readonly habilidades = signal<Habilidad[]>([]);

  readonly cargando = signal(true);
  readonly guardando = signal(false);
  /** La carga del perfil falló (no un 404): no se muestra ni se guarda nada hasta reintentar. */
  readonly errorCarga = signal(false);

  disponibilidadOpciones = [
    { valor: 'inmediata', etiqueta: 'Inmediata' },
    { valor: '1_semana', etiqueta: '1 semana' },
    { valor: '2_semanas', etiqueta: '2 semanas' },
    { valor: '1_mes', etiqueta: '1 mes' },
  ];

  titulosSugeridos: string[] = [
    'Ingeniero de Sistemas',
    'Ingeniero Informático',
    'Licenciado en Computación',
    'Ingeniero en Redes y Telecomunicaciones',
    'Desarrollador Full Stack',
    'Desarrollador Frontend',
    'Desarrollador Backend',
    'Desarrollador Móvil (Flutter / Android)',
    'Analista de Datos / BI',
    'Científico de Datos / IA',
    'Administrador de Base de Datos (DBA)',
    'Ingeniero DevOps / Cloud',
    'Especialista en Ciberseguridad',
    'QA / Tester de Software',
    'Diseñador UI/UX',
    'Scrum Master / Líder Técnico',
    'Soporte Técnico de Sistemas',
  ];

  plantillasResumen = [
    {
      etiqueta: 'Desarrollo de Software',
      texto: 'Profesional enfocado en el desarrollo de software y aplicaciones escalables, con dominio de arquitecturas modernas, buenas prácticas y trabajo colaborativo.',
    },
    {
      etiqueta: 'Egresado Reciente UAGRM',
      texto: 'Egresado con sólida formación en computación y sistemas, proactivo, con alta capacidad de autoaprendizaje y compromiso para generar valor en proyectos tecnológicos.',
    },
    {
      etiqueta: 'Datos e Inteligencia de Negocios',
      texto: 'Especialista en análisis de datos, visualización y modelado de información, orientado a respaldar la toma de decisiones estratégicas en la organización.',
    },
    {
      etiqueta: 'Redes e Infraestructura TI',
      texto: 'Profesional orientado a la administración de infraestructura de redes, seguridad perimetral, configuración de servidores y alta disponibilidad.',
    },
  ];

  institucionesSugeridas: string[] = [
    'UAGRM - Univ. Autónoma Gabriel René Moreno',
    'Postgrado FICCT - UAGRM',
    'Escuela de Ingeniería UAGRM',
    'Platzi',
    'Coursera',
    'Udemy',
    'Cisco Networking Academy',
    'AWS Training & Certification',
    'Google Cloud Skills Boost',
    'Universidad Privada de Santa Cruz (UPSA)',
    'Universidad Católica Boliviana (UCB)',
  ];

  programasSugeridos: string[] = [
    'Ingeniería de Sistemas',
    'Ingeniería Informática',
    'Licenciatura en Computación',
    'Ingeniería en Redes y Telecomunicaciones',
    'Diplomado en Desarrollo Web Full Stack',
    'Diplomado en Ciencia de Datos e Inteligencia Artificial',
    'Certificación Cloud Solutions Architect',
    'CCNA - Enrutamiento y Conmutación',
    'Certificación en Ciberseguridad Defensiva',
    'Scrum Developer Certified',
  ];

  estadosAcademicos = [
    { valor: 'graduado', etiqueta: 'Graduado / Titulado' },
    { valor: 'egresado', etiqueta: 'Egresado' },
    { valor: 'en curso', etiqueta: 'En curso / Cursando' },
    { valor: 'concluido', etiqueta: 'Concluido' },
  ];

  cargosSugeridos: string[] = [
    'Desarrollador Frontend',
    'Desarrollador Backend',
    'Desarrollador Full Stack',
    'Pasante / Practicante de Sistemas',
    'Analista de Sistemas / QA',
    'Soporte Técnico / Helpdesk TI',
    'Administrador de Redes y Servidores',
    'Administrador de Base de Datos (DBA)',
    'Docente / Auxiliar de Cátedra UAGRM',
    'Diseñador UI/UX',
    'Scrum Master / Coordinador TI',
  ];

  idiomasSugeridos: string[] = [
    'Inglés',
    'Español',
    'Portugués',
    'Francés',
    'Alemán',
    'Italiano',
    'Chino Mandarín',
    'Quechua',
    'Guaraní',
  ];

  nivelesIdioma = [
    { valor: 'basico', etiqueta: 'Básico (A1 - A2)' },
    { valor: 'intermedio', etiqueta: 'Intermedio (B1 - B2)' },
    { valor: 'avanzado', etiqueta: 'Avanzado (C1)' },
    { valor: 'fluido', etiqueta: 'Fluido (C2)' },
    { valor: 'nativo', etiqueta: 'Nativo / Bilingüe' },
  ];

  habilidadesSugeridasTecnicas: string[] = [
    'Python',
    'JavaScript',
    'TypeScript',
    'Angular',
    'React',
    'Node.js',
    'Java',
    'C# / .NET',
    'SQL / PostgreSQL',
    'Docker',
    'Git / GitHub',
    'Linux',
    'REST APIs',
    'AWS Cloud',
    'PHP / Laravel',
  ];

  habilidadesSugeridasBlandas: string[] = [
    'Trabajo en equipo',
    'Resolución de problemas',
    'Comunicación asertiva',
    'Liderazgo',
    'Scrum / Metodologías Ágiles',
    'Pensamiento crítico',
    'Adaptabilidad',
    'Gestión del tiempo',
  ];

  nuevaFormacion: Partial<Formacion> = {
    estado_academico: 'graduado',
  };
  nuevaExperiencia: Partial<Experiencia> = {};
  nuevoIdioma: Partial<Idioma> = {
    idioma: 'Inglés',
    nivel: 'intermedio',
  };
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
    this.errorCarga.set(false);
    const headers = this.headers();

    forkJoin({
      // Solo un 404 (todavía sin perfil) arma el perfil en blanco. Ante otro error no se carga nada:
      // el formulario se guarda solo y pisaría los datos reales con los vacíos.
      perfil: this.http
        .get<Perfil>(this.apiBase, { headers })
        .pipe(catchError((err: HttpErrorResponse) => of(err.status === 404 ? null : ERROR_DE_CARGA))),
      formaciones: this.http.get<Formacion[]>(`${this.apiBase}/formacion`, { headers }).pipe(catchError(() => of([]))),
      experiencias: this.http.get<Experiencia[]>(`${this.apiBase}/experiencia`, { headers }).pipe(catchError(() => of([]))),
      idiomas: this.http.get<Idioma[]>(`${this.apiBase}/idiomas`, { headers }).pipe(catchError(() => of([]))),
      certificaciones: this.http.get<Certificacion[]>(`${this.apiBase}/certificaciones`, { headers }).pipe(catchError(() => of([]))),
      habilidades: this.http.get<Habilidad[]>(`${this.apiBase}/habilidades`, { headers }).pipe(catchError(() => of([]))),
    }).subscribe({
      next: (resp) => {
        if (resp.perfil === ERROR_DE_CARGA) {
          this.errorCarga.set(true);
          this.toast.error('No se pudo cargar tu perfil. Reintentá en unos segundos.');
        } else if (resp.perfil) {
          this.perfil.set(resp.perfil);
        } else if (!this.perfil()) {
          this.perfil.set({
            nombres: '',
            apellidos: '',
            estado_validacion: 'PENDIENTE',
            porcentaje_completitud: 0,
            disponibilidad: null,
            carrera_id: null,
            anio_egreso: null,
            matricula: null,
            titulo_profesional: '',
            resumen_profesional: '',
          });
        }
        this.formaciones.set(resp.formaciones ?? []);
        this.experiencias.set(resp.experiencias ?? []);
        this.idiomas.set(resp.idiomas ?? []);
        this.certificaciones.set(resp.certificaciones ?? []);
        this.habilidades.set(resp.habilidades ?? []);
        this.cargando.set(false);
      },
      error: () => this.cargando.set(false),
    });
  }

  private refrescarPerfil(): void {
    this.http
      .get<Perfil>(this.apiBase, { headers: this.headers() })
      .subscribe({
        next: (perfil) => this.perfil.set(perfil),
        error: () => {},
      });
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
          this.toast.success('Datos profesionales guardados correctamente.');
          this.refrescarPerfil();
        },
        error: () => {
          this.guardando.set(false);
          this.toast.error('No se pudo guardar la información del perfil.');
        },
      });
  }

  agregarFormacion(): void {
    if (!this.nuevaFormacion.institucion || !this.nuevaFormacion.programa) {
      this.toast.warning('Ingresa la institución y el programa académico.');
      return;
    }
    this.http.post<Formacion>(`${this.apiBase}/formacion`, this.nuevaFormacion, { headers: this.headers() }).subscribe({
      next: () => {
        this.nuevaFormacion = {};
        this.toast.success('Formación académica agregada.');
        this.cargarTodo();
      },
      error: () => this.toast.error('Error al agregar formación académica.'),
    });
  }

  eliminarFormacion(id: string): void {
    this.http.delete(`${this.apiBase}/formacion/${id}`, { headers: this.headers() }).subscribe({
      next: () => {
        this.toast.info('Formación eliminada.');
        this.cargarTodo();
      },
      error: () => this.toast.error('Error al eliminar formación.'),
    });
  }

  agregarExperiencia(): void {
    if (!this.nuevaExperiencia.empresa || !this.nuevaExperiencia.cargo) {
      this.toast.warning('Ingresa el nombre de la empresa y el cargo.');
      return;
    }
    this.http
      .post<Experiencia>(`${this.apiBase}/experiencia`, this.nuevaExperiencia, { headers: this.headers() })
      .subscribe({
        next: () => {
          this.nuevaExperiencia = {};
          this.toast.success('Experiencia laboral registrada.');
          this.cargarTodo();
        },
        error: () => this.toast.error('Error al registrar experiencia laboral.'),
      });
  }

  eliminarExperiencia(id: string): void {
    this.http.delete(`${this.apiBase}/experiencia/${id}`, { headers: this.headers() }).subscribe({
      next: () => {
        this.toast.info('Experiencia eliminada.');
        this.cargarTodo();
      },
      error: () => this.toast.error('Error al eliminar experiencia.'),
    });
  }

  agregarIdioma(): void {
    if (!this.nuevoIdioma.idioma) {
      this.toast.warning('Ingresa el nombre del idioma.');
      return;
    }
    this.http.post<Idioma>(`${this.apiBase}/idiomas`, this.nuevoIdioma, { headers: this.headers() }).subscribe({
      next: () => {
        this.nuevoIdioma = { nivel: 'basico' };
        this.toast.success('Idioma registrado.');
        this.cargarTodo();
      },
      error: () => this.toast.error('Error al agregar idioma.'),
    });
  }

  eliminarIdioma(id: string): void {
    this.http.delete(`${this.apiBase}/idiomas/${id}`, { headers: this.headers() }).subscribe({
      next: () => {
        this.toast.info('Idioma eliminado.');
        this.cargarTodo();
      },
      error: () => this.toast.error('Error al eliminar idioma.'),
    });
  }

  agregarHabilidad(): void {
    const nombre = this.habilidadTexto.trim();
    if (!nombre) return;
    const nombres = [...this.habilidades().map((h) => h.nombre), nombre];
    this.http.put<Habilidad[]>(`${this.apiBase}/habilidades`, { habilidades: nombres }, { headers: this.headers() }).subscribe({
      next: () => {
        this.habilidadTexto = '';
        this.toast.success('Habilidad agregada.');
        this.cargarTodo();
      },
      error: () => this.toast.error('Error al agregar habilidad.'),
    });
  }

  eliminarHabilidad(nombre: string): void {
    const nombres = this.habilidades()
      .map((h) => h.nombre)
      .filter((n) => n !== nombre);
    this.http.put<Habilidad[]>(`${this.apiBase}/habilidades`, { habilidades: nombres }, { headers: this.headers() }).subscribe({
      next: () => {
        this.toast.info('Habilidad removida.');
        this.cargarTodo();
      },
      error: () => this.toast.error('Error al remover habilidad.'),
    });
  }

  tieneHabilidad(nombre: string): boolean {
    return this.habilidades().some((h) => h.nombre.toLowerCase() === nombre.toLowerCase());
  }

  agregarHabilidadRapida(nombre: string): void {
    if (this.tieneHabilidad(nombre)) {
      this.toast.info(`"${nombre}" ya está en tu lista de habilidades.`);
      return;
    }
    const nombres = [...this.habilidades().map((h) => h.nombre), nombre];
    this.http.put<Habilidad[]>(`${this.apiBase}/habilidades`, { habilidades: nombres }, { headers: this.headers() }).subscribe({
      next: () => {
        this.toast.success(`Habilidad "${nombre}" añadida.`);
        this.cargarTodo();
      },
      error: () => this.toast.error('Error al agregar habilidad.'),
    });
  }

  seleccionarTitulo(titulo: string): void {
    this.actualizarPerfil({ titulo_profesional: titulo });
    this.guardarDatosBasicos();
  }

  aplicarPlantillaResumen(texto: string): void {
    this.actualizarPerfil({ resumen_profesional: texto });
    this.guardarDatosBasicos();
    this.toast.success('Plantilla aplicada. Puedes editarla o personalizarla en cualquier momento.');
  }

  seleccionarDisponibilidad(valor: string): void {
    this.actualizarPerfil({ disponibilidad: valor });
    this.guardarDatosBasicos();
  }

  seleccionarInstitucion(inst: string): void {
    this.nuevaFormacion.institucion = inst;
  }

  seleccionarPrograma(prog: string): void {
    this.nuevaFormacion.programa = prog;
  }

  seleccionarCargo(cargo: string): void {
    this.nuevaExperiencia.cargo = cargo;
  }

  descargarCv(): void {
    this.http.get(`${this.apiBase}/cv`, { headers: this.headers(), responseType: 'blob', observe: 'response' }).subscribe({
      next: (respuesta) => {
        const disposicion = respuesta.headers.get('content-disposition') || '';
        const coincidencia = /filename=([^;]+)/.exec(disposicion);
        const nombreArchivo = coincidencia ? coincidencia[1].trim().replace(/"/g, '') : 'CV_EGRESA.pdf';
        const blob = respuesta.body as Blob;
        const url = window.URL.createObjectURL(blob);
        const enlace = document.createElement('a');
        enlace.href = url;
        enlace.download = nombreArchivo;
        enlace.click();
        window.URL.revokeObjectURL(url);
        this.toast.success('CV descargado exitosamente.');
      },
      error: () => {
        this.toast.error('No se pudo generar o descargar el CV. Asegúrate de haber completado tus datos.');
      },
    });
  }
}
