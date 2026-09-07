<<<<<<< HEAD
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../features/auth/auth.service';
import {
  FiltrosBusquedaVacantes,
  FiltrosDisponibles,
  VacanteDetalle,
  VacantesPaginadas,
} from '../models/vacante.models';
=======
import { HttpClient, HttpErrorResponse, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, shareReplay, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  FiltrosBusquedaVacantes,
  FiltrosDisponibles,
  JobStatus,
  Vacante,
  VacanteCambioEstadoRequest,
  VacanteCreateRequest,
  VacanteDetalle,
  VacanteFiltros,
  VacanteModeracionRequest,
  VacantePaginadaResponse,
  VacanteUpdateRequest,
  VacantesPaginadas,
} from '../models/vacante.models';
import { ToastService } from './toast.service';

export interface CatalogoItem {
  id: string;
  nombre: string;
}
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad

@Injectable({
  providedIn: 'root',
})
export class VacanteService {
  private readonly http = inject(HttpClient);
<<<<<<< HEAD
  private readonly auth = inject(AuthService);
  private readonly apiUrl = `${environment.apiUrl}/vacantes`;

  private headers(): HttpHeaders {
    const token = this.auth.token();
    if (token) {
      return new HttpHeaders({ Authorization: `Bearer ${token}` });
    }
    return new HttpHeaders();
  }

  /** Busca vacantes aplicando filtros combinados y paginación */
  buscarVacantes(filtros: FiltrosBusquedaVacantes = {}): Observable<VacantesPaginadas> {
    let params = new HttpParams();

    if (filtros.q && filtros.q.trim()) {
      params = params.set('q', filtros.q.trim());
    }
    if (filtros.carrera_id) {
      params = params.set('carrera_id', filtros.carrera_id);
    }
    if (filtros.categoria_id) {
      params = params.set('categoria_id', filtros.categoria_id);
    }
    if (filtros.ciudad) {
      params = params.set('ciudad', filtros.ciudad);
    }
    if (filtros.modalidad) {
      params = params.set('modalidad', filtros.modalidad);
    }
    if (filtros.jornada) {
      params = params.set('jornada', filtros.jornada);
    }
    if (filtros.seniority) {
      params = params.set('seniority', filtros.seniority);
    }
=======
  private readonly toast = inject(ToastService);
  private readonly apiUrl = `${environment.apiUrl}/vacantes`;
  private readonly catalogosUrl = `${environment.apiUrl}/catalogos`;

  private _headers(): HttpHeaders {
    const token = localStorage.getItem('token') || '';
    return new HttpHeaders({
      Authorization: `Bearer ${token}`,
    });
  }

  /**
   * Publica o registra una nueva vacante en el sistema.
   * @param data Datos de la vacante y habilidades requeridas.
   */
  crearVacante(data: VacanteCreateRequest): Observable<Vacante> {
    return this.http.post<Vacante>(this.apiUrl, data, { headers: this._headers() }).pipe(
      catchError((error: HttpErrorResponse) => this._handleError(error, 'Error al crear la vacante'))
    );
  }

  /**
   * Obtiene la lista paginada de vacantes de la empresa autenticada.
   * @param filtros Filtro opcional por estado y parámetros de paginación.
   */
  listarMisVacantes(filtros?: VacanteFiltros): Observable<VacantePaginadaResponse> {
    const params = this._construirParams(filtros);
    return this.http.get<VacantePaginadaResponse>(`${this.apiUrl}/mis-vacantes`, {
      headers: this._headers(),
      params,
    }).pipe(
      catchError((error: HttpErrorResponse) =>
        this._handleError(error, 'Error al cargar las vacantes de la empresa')
      )
    );
  }

  /**
   * Obtiene la lista paginada de vacantes públicas y publicadas con filtros.
   * @param filtros Criterios de búsqueda (texto, categoría, ciudad, modalidad, salario, etc.).
   */
  listarVacantesPublicas(filtros?: VacanteFiltros): Observable<VacantePaginadaResponse> {
    const params = this._construirParams(filtros);
    return this.http.get<VacantePaginadaResponse>(this.apiUrl, {
      headers: this._headers(),
      params,
    }).pipe(
      catchError((error: HttpErrorResponse) =>
        this._handleError(error, 'Error al buscar vacantes')
      )
    );
  }

  /**
   * Obtiene los detalles completos de una vacante por su ID.
   * @param id Identificador UUID de la vacante.
   */
  obtenerVacante(id: string): Observable<Vacante> {
    return this.http.get<Vacante>(`${this.apiUrl}/${id}`, { headers: this._headers() }).pipe(
      catchError((error: HttpErrorResponse) =>
        this._handleError(error, 'Error al obtener los detalles de la vacante')
      )
    );
  }

  /**
   * Actualiza los datos o habilidades de una vacante existente.
   * @param id Identificador UUID de la vacante.
   * @param data Campos a actualizar.
   */
  actualizarVacante(id: string, data: VacanteUpdateRequest): Observable<Vacante> {
    return this.http.put<Vacante>(`${this.apiUrl}/${id}`, data, { headers: this._headers() }).pipe(
      catchError((error: HttpErrorResponse) =>
        this._handleError(error, 'Error al actualizar la vacante')
      )
    );
  }

  /**
   * Cambia el estado del ciclo de vida de la vacante (draft, published, paused, closed).
   * @param id Identificador UUID de la vacante.
   * @param estado Nuevo estado a asignar.
   */
  cambiarEstado(id: string, estado: JobStatus): Observable<Vacante> {
    const payload: VacanteCambioEstadoRequest = { status: estado };
    return this.http.patch<Vacante>(`${this.apiUrl}/${id}/estado`, payload, {
      headers: this._headers(),
    }).pipe(
      catchError((error: HttpErrorResponse) =>
        this._handleError(error, 'Error al cambiar el estado de la vacante')
      )
    );
  }

  /**
   * Elimina definitivamente una vacante.
   * @param id Identificador UUID de la vacante.
   */
  eliminarVacante(id: string): Observable<{ mensaje: string }> {
    return this.http.delete<{ mensaje: string }>(`${this.apiUrl}/${id}`, {
      headers: this._headers(),
    }).pipe(
      catchError((error: HttpErrorResponse) =>
        this._handleError(error, 'Error al eliminar la vacante')
      )
    );
  }

  // ─── Moderación institucional (HU-12) ────────────────────────────────────

  /** Lista las vacantes pendientes de revisión (solo admin/moderador). */
  listarPendientesRevision(page = 1, pageSize = 10): Observable<VacantePaginadaResponse> {
    const params = new HttpParams().set('page', String(page)).set('page_size', String(pageSize));
    return this.http
      .get<VacantePaginadaResponse>(`${environment.apiUrl}/validacion/vacantes/pendientes`, {
        headers: this._headers(),
        params,
      })
      .pipe(
        catchError((error: HttpErrorResponse) =>
          this._handleError(error, 'Error al cargar las vacantes pendientes de revisión')
        )
      );
  }

  /** Aprueba o rechaza (con motivo) una vacante pendiente de revisión. */
  moderarVacante(id: string, data: VacanteModeracionRequest): Observable<Vacante> {
    return this.http
      .post<Vacante>(`${environment.apiUrl}/validacion/vacantes/${id}/decision`, data, {
        headers: this._headers(),
      })
      .pipe(
        catchError((error: HttpErrorResponse) => this._handleError(error, 'Error al moderar la vacante'))
      );
  }

  // ─── Catálogos de Apoyo para Formularios ─────────────────────────────────

  /** Obtiene las categorías de ofertas laborales para selectores. */
  obtenerCategorias(): Observable<CatalogoItem[]> {
    return this.http.get<CatalogoItem[]>(`${this.catalogosUrl}/categorias-oferta`, {
      headers: this._headers(),
    }).pipe(
      catchError((error: HttpErrorResponse) =>
        this._handleError(error, 'Error al cargar catálogo de categorías')
      )
    );
  }

  /** Obtiene el catálogo global de habilidades técnicas y blandas. */
  obtenerHabilidades(): Observable<CatalogoItem[]> {
    return this.http.get<CatalogoItem[]>(`${this.catalogosUrl}/habilidades`, {
      headers: this._headers(),
    }).pipe(
      catchError((error: HttpErrorResponse) =>
        this._handleError(error, 'Error al cargar catálogo de habilidades')
      )
    );
  }

  /** Obtiene el catálogo de ciudades disponibles. */
  obtenerCiudades(): Observable<{ nombre: string }[]> {
    return this.http.get<{ nombre: string }[]>(`${this.catalogosUrl}/ciudades`, {
      headers: this._headers(),
    }).pipe(
      catchError((error: HttpErrorResponse) =>
        this._handleError(error, 'Error al cargar catálogo de ciudades')
      )
    );
  }

  // ─── Búsqueda avanzada con afinidad (HU-13) ──────────────────────────────
  // Vive bajo /vacantes/buscar en el backend, separado del listado simple de
  // arriba para no romper su contrato (usado también por la app móvil).

  private filtrosCache$: Observable<FiltrosDisponibles> | null = null;

  /** Busca vacantes aplicando filtros combinados, con cálculo de afinidad si hay sesión. */
  buscarVacantes(filtros: FiltrosBusquedaVacantes = {}): Observable<VacantesPaginadas> {
    let params = new HttpParams();

    if (filtros.q && filtros.q.trim()) params = params.set('q', filtros.q.trim());
    if (filtros.carrera_id) params = params.set('carrera_id', filtros.carrera_id);
    if (filtros.categoria_id) params = params.set('categoria_id', filtros.categoria_id);
    if (filtros.ciudad) params = params.set('ciudad', filtros.ciudad);
    if (filtros.modalidad) params = params.set('modalidad', filtros.modalidad);
    if (filtros.jornada) params = params.set('jornada', filtros.jornada);
    if (filtros.seniority) params = params.set('seniority', filtros.seniority);
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
    if (filtros.salario_min !== undefined && filtros.salario_min !== null) {
      params = params.set('salario_min', String(filtros.salario_min));
    }
    if (filtros.salario_max !== undefined && filtros.salario_max !== null) {
      params = params.set('salario_max', String(filtros.salario_max));
    }
<<<<<<< HEAD
    if (filtros.ordenar_por) {
      params = params.set('ordenar_por', filtros.ordenar_por);
    }
    if (filtros.limit !== undefined) {
      params = params.set('limit', String(filtros.limit));
    }
    if (filtros.offset !== undefined) {
      params = params.set('offset', String(filtros.offset));
    }

    return this.http.get<VacantesPaginadas>(this.apiUrl, {
      headers: this.headers(),
      params,
    });
  }

  private filtrosCache$: Observable<FiltrosDisponibles> | null = null;

  /** Obtiene las opciones de catálogo dinámicas para los filtros con caché en memoria */
  obtenerFiltrosDisponibles(): Observable<FiltrosDisponibles> {
    if (!this.filtrosCache$) {
      this.filtrosCache$ = this.http
        .get<FiltrosDisponibles>(`${this.apiUrl}/filtros`, {
          headers: this.headers(),
        })
=======
    if (filtros.ordenar_por) params = params.set('ordenar_por', filtros.ordenar_por);
    if (filtros.limit !== undefined) params = params.set('limit', String(filtros.limit));
    if (filtros.offset !== undefined) params = params.set('offset', String(filtros.offset));

    return this.http
      .get<VacantesPaginadas>(`${this.apiUrl}/buscar`, { headers: this._headers(), params })
      .pipe(catchError((error: HttpErrorResponse) => this._handleError(error, 'Error al buscar vacantes')));
  }

  /** Opciones de catálogo dinámicas para los filtros de búsqueda, con caché en memoria. */
  obtenerFiltrosDisponibles(): Observable<FiltrosDisponibles> {
    if (!this.filtrosCache$) {
      this.filtrosCache$ = this.http
        .get<FiltrosDisponibles>(`${this.apiUrl}/buscar/filtros`, { headers: this._headers() })
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
        .pipe(shareReplay(1));
    }
    return this.filtrosCache$;
  }

<<<<<<< HEAD
  /** Obtiene el detalle completo de una vacante */
  obtenerDetalle(vacanteId: string): Observable<VacanteDetalle> {
    return this.http.get<VacanteDetalle>(`${this.apiUrl}/${vacanteId}`, {
      headers: this.headers(),
    });
  }
}

=======
  /** Detalle enriquecido (afinidad, contacto) de una vacante desde la búsqueda. */
  obtenerDetalle(vacanteId: string): Observable<VacanteDetalle> {
    return this.http
      .get<VacanteDetalle>(`${this.apiUrl}/buscar/${vacanteId}`, { headers: this._headers() })
      .pipe(catchError((error: HttpErrorResponse) => this._handleError(error, 'Error al obtener el detalle de la vacante')));
  }

  // ─── Utilidades Privadas ────────────────────────────────────────────────

  private _construirParams(filtros?: VacanteFiltros): HttpParams {
    let params = new HttpParams();
    if (!filtros) return params;

    if (filtros.q) params = params.set('q', filtros.q.trim());
    if (filtros.category_id) params = params.set('category_id', filtros.category_id);
    if (filtros.city) params = params.set('city', filtros.city.trim());
    if (filtros.work_modality) params = params.set('work_modality', filtros.work_modality);
    if (filtros.seniority_level) params = params.set('seniority_level', filtros.seniority_level);
    if (filtros.employment_type) params = params.set('employment_type', filtros.employment_type);
    if (filtros.salary_min !== undefined && filtros.salary_min !== null) {
      params = params.set('salary_min', String(filtros.salary_min));
    }
    if (filtros.estado) params = params.set('estado', filtros.estado);
    if (filtros.page) params = params.set('page', String(filtros.page));
    if (filtros.page_size) params = params.set('page_size', String(filtros.page_size));

    return params;
  }

  private _handleError(error: HttpErrorResponse, mensajeFallback: string): Observable<never> {
    let mensaje = mensajeFallback;
    if (error.error?.detail) {
      mensaje = typeof error.error.detail === 'string'
        ? error.error.detail
        : JSON.stringify(error.error.detail);
    } else if (error.message) {
      mensaje = error.message;
    }

    this.toast.error(mensaje);
    return throwError(() => new Error(mensaje));
  }
}
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
