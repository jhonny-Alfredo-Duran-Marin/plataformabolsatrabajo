import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';
import { environment } from '../../../../environments/environment';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-registro-egresado',
  standalone: true,
  imports: [ReactiveFormsModule, CommonModule, RouterLink],
  templateUrl: './registro-egresado.html',
  styleUrl: './registro-egresado.scss'
})
export class RegistroEgresado implements OnInit {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private router = inject(Router);

  registroForm: FormGroup = this.fb.group({
    nombres: ['', Validators.required],
    apellidos: ['', Validators.required],
    ci: ['', Validators.required],
    correo: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    carrera_id: ['', Validators.required],
    anio_egreso: ['', [Validators.required, Validators.min(1950), Validators.max(new Date().getFullYear())]],
    matricula: ['']
  });

  carreras: any[] = [];
  isCargandoCarreras = true;
  carrerasError = '';
  mensajeExito = '';
  mensajeError = '';
  isLoading = false;

  ngOnInit(): void {
    this.http.get<any[]>(`${environment.apiUrl}/catalogos/carreras`).subscribe({
      next: (data) => {
        this.carreras = data;
        this.isCargandoCarreras = false;
      },
      error: (err) => {
        console.error('Error cargando carreras', err);
        this.carrerasError = err.message || 'Desconocido';
        this.isCargandoCarreras = false;
      }
    });
  }

  onSubmit(): void {
    if (this.registroForm.invalid) {
      this.registroForm.markAllAsTouched();
      return;
    }
    
    this.isLoading = true;
    this.mensajeError = '';
    this.mensajeExito = '';
    
    this.http.post(`${environment.apiUrl}/auth/registro/egresado`, this.registroForm.value).subscribe({
      next: (res: any) => {
        this.mensajeExito = 'Tus datos fueron registrados exitosamente.';
        this.isLoading = false;
        setTimeout(() => this.router.navigate(['/auth/login']), 3000);
      },
      error: (err) => {
        this.isLoading = false;
        if (err.status === 409) {
           this.mensajeError = err.error.detail || 'El CI o correo ya están registrados.';
        } else {
           this.mensajeError = 'Ocurrió un error inesperado al registrarte.';
        }
      }
    });
  }
}
