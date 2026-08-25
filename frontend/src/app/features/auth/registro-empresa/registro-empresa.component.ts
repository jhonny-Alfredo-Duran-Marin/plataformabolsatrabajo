import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { AuthService } from '../auth.service';
import { RegistroEmpresaRequest } from '../../../core/models/auth.models';

/** Validador personalizado para asegurar que las contraseñas coincidan */
export const passwordsMatchValidator: ValidatorFn = (
  control: AbstractControl
): ValidationErrors | null => {
  const password = control.get('password');
  const confirmPassword = control.get('confirmPassword');

  if (password && confirmPassword && password.value !== confirmPassword.value) {
    return { passwordsMismatch: true };
  }
  return null;
};

@Component({
  selector: 'app-registro-empresa',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './registro-empresa.component.html',
  styleUrl: './registro-empresa.component.scss',
})
export class RegistroEmpresaComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);

  // Estados de la vista
  isLoading = false;
  errorMessage: string | null = null;
  successMessage: string | null = null;
  isSubmittedSuccess = false;

  // Sectores y tamaños sugeridos
  sectores: string[] = [
    'Tecnología e Informática',
    'Banca, Finanzas y Seguros',
    'Comercio y Retail',
    'Industria y Manufactura',
    'Salud y Farmacéutica',
    'Educación y Capacitación',
    'Construcción e Inmobiliaria',
    'Agroindustria y Ganadería',
    'Telecomunicaciones',
    'Servicios Profesionales y Consultoría',
    'Otro',
  ];

  tamanios: string[] = [
    'Microempresa (1 - 10 empleados)',
    'Pequeña (11 - 50 empleados)',
    'Mediana (51 - 200 empleados)',
    'Grande (+200 empleados)',
  ];

  // Formulario reactivo
  registroForm: FormGroup = this.fb.group(
    {
      razon_social: [
        '',
        [Validators.required, Validators.minLength(2), Validators.maxLength(200)],
      ],
      nit: [
        '',
        [
          Validators.required,
          Validators.minLength(4),
          Validators.maxLength(30),
          Validators.pattern(/^[0-9A-Za-z-]+$/),
        ],
      ],
      sector: ['', [Validators.required]],
      tamanio: [''],
      direccion: ['', [Validators.maxLength(255)]],
      telefono: ['', [Validators.maxLength(30)]],
      sitio_web: ['', [Validators.maxLength(255)]],
      descripcion: [''],
      representante_legal: ['', [Validators.maxLength(150)]],
      correo: [
        '',
        [
          Validators.required,
          Validators.email,
          Validators.maxLength(150),
        ],
      ],
      password: [
        '',
        [
          Validators.required,
          Validators.minLength(8),
        ],
      ],
      confirmPassword: ['', [Validators.required]],
    },
    { validators: passwordsMatchValidator }
  );

  get f() {
    return this.registroForm.controls;
  }

  onSubmit(): void {
    this.errorMessage = null;

    if (this.registroForm.invalid) {
      this.registroForm.markAllAsTouched();
      this.errorMessage =
        'Por favor completa todos los campos requeridos correctamente.';
      return;
    }

    this.isLoading = true;

    const formValues = this.registroForm.value;
    const payload: RegistroEmpresaRequest = {
      razon_social: formValues.razon_social.trim(),
      nit: formValues.nit.trim(),
      correo: formValues.correo.trim().toLowerCase(),
      password: formValues.password,
      sector: formValues.sector ? formValues.sector : undefined,
      tamanio: formValues.tamanio ? formValues.tamanio : undefined,
      direccion: formValues.direccion ? formValues.direccion.trim() : undefined,
      telefono: formValues.telefono ? formValues.telefono.trim() : undefined,
      sitio_web: formValues.sitio_web ? formValues.sitio_web.trim() : undefined,
      descripcion: formValues.descripcion ? formValues.descripcion.trim() : undefined,
      representante_legal: formValues.representante_legal
        ? formValues.representante_legal.trim()
        : undefined,
    };

    this.authService.registrarEmpresa(payload).subscribe({
      next: (res) => {
        this.isLoading = false;
        this.isSubmittedSuccess = true;
        this.successMessage =
          res.detail ||
          'Solicitud de registro recibida. Queda pendiente de autorización institucional.';
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage =
          err.message || 'No se pudo completar el registro de la empresa.';
      },
    });
  }

  resetForm(): void {
    this.registroForm.reset();
    this.isSubmittedSuccess = false;
    this.errorMessage = null;
    this.successMessage = null;
  }
}

