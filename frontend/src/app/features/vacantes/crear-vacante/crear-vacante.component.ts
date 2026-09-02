import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  EmploymentType,
  JobSkillItemRequest,
  SeniorityLevel,
  SkillImportance,
  SkillProficiencyLevel,
  VacanteCreateRequest,
  WorkModality,
} from '../../../core/models/vacante.models';
import { ToastService } from '../../../core/services/toast.service';
import {
  CatalogoItem,
  VacanteService,
} from '../../../core/services/vacante.service';

interface HabilidadSeleccionada {
  skill_id: string;
  skill_name: string;
  min_proficiency: SkillProficiencyLevel;
  importance: SkillImportance;
  weight?: number;
}

/**
 * Componente para el registro y publicación de nuevas ofertas laborales por parte de empresas.
 */
@Component({
  selector: 'app-crear-vacante',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, RouterLink],
  templateUrl: './crear-vacante.component.html',
  styleUrl: './crear-vacante.component.scss',
})
export class CrearVacanteComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly vacanteService = inject(VacanteService);
  private readonly toast = inject(ToastService);

  form!: FormGroup;
  guardando = false;
  cargandoCatalogos = false;

  categorias: CatalogoItem[] = [];
  habilidadesCatalogo: CatalogoItem[] = [];
  habilidadesSeleccionadas: HabilidadSeleccionada[] = [];

  // Controles auxiliares para agregar habilidades
  skillSeleccionadaId = '';
  skillNivelSeleccionado: SkillProficiencyLevel = 'intermediate';
  skillEsRequerida = false;
  skillPeso: number | null = null;

  readonly nivelesSeniority: { valor: SeniorityLevel; label: string }[] = [
    { valor: 'internship', label: 'Pasantía / Prácticas' },
    { valor: 'junior', label: 'Junior (0 - 2 años)' },
    { valor: 'mid', label: 'Semi Senior / Mid (2 - 5 años)' },
    { valor: 'senior', label: 'Senior (5+ años)' },
    { valor: 'lead', label: 'Líder Técnico / Lead' },
  ];

  readonly tiposEmpleo: { valor: EmploymentType; label: string }[] = [
    { valor: 'permanent', label: 'Tiempo Completo (Indefinido)' },
    { valor: 'temporary', label: 'Temporal' },
    { valor: 'contract', label: 'Por Contrato' },
    { valor: 'internship', label: 'Pasantía' },
    { valor: 'part_time', label: 'Medio Tiempo' },
    { valor: 'freelance', label: 'Freelance / Consultoría' },
  ];

  readonly modalidades: { valor: WorkModality; label: string }[] = [
    { valor: 'onsite', label: 'Presencial' },
    { valor: 'hybrid', label: 'Híbrido' },
    { valor: 'remote', label: 'Remoto' },
  ];

  readonly nivelesNivelHabilidad: { valor: SkillProficiencyLevel; label: string }[] = [
    { valor: 'basic', label: 'Básico' },
    { valor: 'intermediate', label: 'Intermedio' },
    { valor: 'advanced', label: 'Avanzado' },
    { valor: 'expert', label: 'Experto' },
  ];

  readonly nivelesEducacion: { valor: string; label: string }[] = [
    { valor: 'technical', label: 'Técnico Superior' },
    { valor: 'undergraduate', label: 'Licenciatura / Ingeniería' },
    { valor: 'postgraduate', label: 'Especialidad / Diplomado' },
    { valor: 'master', label: 'Maestría' },
  ];

  ngOnInit(): void {
    this._initForm();
    this._cargarCatalogos();
  }

  private _initForm(): void {
    this.form = this.fb.group({
      title: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(200)]],
      description: ['', [Validators.required, Validators.minLength(10)]],
      responsibilities_json: [''],
      requirements_json: [''],
      category_id: [''],
      seniority_level: ['junior'],
      employment_type: ['permanent'],
      work_modality: ['onsite'],
      min_education_level: ['undergraduate'],
      min_years_experience: [0, [Validators.min(0)]],
      country_code: ['BO'],
      city: ['Santa Cruz de la Sierra', [Validators.required]],
      salary_min: [null, [Validators.min(0)]],
      salary_max: [null, [Validators.min(0)]],
      currency: ['BOB'],
      salary_visible: [true],
      positions_available: [1, [Validators.required, Validators.min(1)]],
      application_deadline: [null],
    });
  }

  private _cargarCatalogos(): void {
    this.cargandoCatalogos = true;
    this.vacanteService.obtenerCategorias().subscribe({
      next: (data) => (this.categorias = data),
      error: () => {},
    });

    this.vacanteService.obtenerHabilidades().subscribe({
      next: (data) => {
        this.habilidadesCatalogo = data;
        this.cargandoCatalogos = false;
      },
      error: () => (this.cargandoCatalogos = false),
    });
  }

  // ─── Manejo de Habilidades ───────────────────────────────────────────────

  agregarHabilidad(): void {
    if (!this.skillSeleccionadaId) {
      this.toast.warning('Selecciona una habilidad del catálogo para agregar.');
      return;
    }

    const yaExiste = this.habilidadesSeleccionadas.some(
      (h) => h.skill_id === this.skillSeleccionadaId
    );
    if (yaExiste) {
      this.toast.warning('Esta habilidad ya ha sido agregada.');
      return;
    }

    const skillObj = this.habilidadesCatalogo.find(
      (h) => h.id === this.skillSeleccionadaId
    );
    if (!skillObj) return;

    this.habilidadesSeleccionadas.push({
      skill_id: skillObj.id,
      skill_name: skillObj.nombre,
      min_proficiency: this.skillNivelSeleccionado,
      importance: this.skillEsRequerida ? 'required' : 'preferred',
      weight: this.skillPeso !== null ? Number(this.skillPeso) : undefined,
    });

    // Resetear controles
    this.skillSeleccionadaId = '';
    this.skillNivelSeleccionado = 'intermediate';
    this.skillEsRequerida = false;
    this.skillPeso = null;
  }

  removerHabilidad(index: number): void {
    this.habilidadesSeleccionadas.splice(index, 1);
  }

  // ─── Envío del Formulario ────────────────────────────────────────────────

  guardar(comoBorrador = false): void {
    if (!comoBorrador && this.form.invalid) {
      this.form.markAllAsTouched();
      this.toast.error('Por favor completa todos los campos obligatorios.');
      return;
    }

    // Validar rango salarial
    const salMin = this.form.value.salary_min;
    const salMax = this.form.value.salary_max;
    if (salMin !== null && salMax !== null && Number(salMin) > Number(salMax)) {
      this.toast.error('El salario mínimo no puede superar al salario máximo.');
      return;
    }

    this.guardando = true;
    const formVal = this.form.value;

    const skillsDto: JobSkillItemRequest[] = this.habilidadesSeleccionadas.map((h) => ({
      skill_id: h.skill_id,
      min_proficiency: h.min_proficiency,
      importance: h.importance,
      weight: h.weight,
    }));

    const aLineas = (texto: string | null | undefined): string[] | null => {
      if (!texto) return null;
      const lineas = texto.split('\n').map((l) => l.trim()).filter((l) => l.length > 0);
      return lineas.length > 0 ? lineas : null;
    };

    const payload: VacanteCreateRequest = {
      title: formVal.title,
      description: formVal.description,
      responsibilities_json: aLineas(formVal.responsibilities_json),
      requirements_json: aLineas(formVal.requirements_json),
      category_id: formVal.category_id || null,
      seniority_level: formVal.seniority_level,
      employment_type: formVal.employment_type,
      work_modality: formVal.work_modality || 'onsite',
      min_education_level: formVal.min_education_level || null,
      min_years_experience: formVal.min_years_experience ? Number(formVal.min_years_experience) : 0,
      country_code: formVal.country_code || 'BO',
      city: formVal.city,
      salary_min: formVal.salary_min !== null ? Number(formVal.salary_min) : null,
      salary_max: formVal.salary_max !== null ? Number(formVal.salary_max) : null,
      currency: formVal.currency || 'BOB',
      salary_visible: !!formVal.salary_visible,
      positions_available: formVal.positions_available ? Number(formVal.positions_available) : 1,
      status: comoBorrador ? 'draft' : 'published',
      application_deadline: formVal.application_deadline ? new Date(formVal.application_deadline).toISOString() : null,
      skills: skillsDto,
    };

    this.vacanteService.crearVacante(payload).subscribe({
      next: (resp) => {
        this.guardando = false;
        if (resp.status === 'draft' && !comoBorrador) {
          this.toast.warning(
            'Vacante guardada en borrador. Se publicará cuando tu empresa sea verificada por la UAGRM.'
          );
        } else if (resp.status === 'pending_review') {
          this.toast.success(
            'Vacante enviada a revisión institucional. Se publicará cuando un moderador la apruebe.'
          );
        } else {
          this.toast.success(
            comoBorrador
              ? 'Borrador guardado exitosamente.'
              : '¡Vacante publicada con éxito!'
          );
        }
        this.router.navigate(['/vacantes/mis-vacantes']);
      },
      error: () => {
        this.guardando = false;
      },
    });
  }
}
