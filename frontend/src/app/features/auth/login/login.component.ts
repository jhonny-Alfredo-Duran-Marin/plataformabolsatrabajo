import { Component, signal, inject, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink, LoadingSpinnerComponent],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent implements OnInit {
  private fb       = inject(FormBuilder);
  private auth     = inject(AuthService);
  private toast    = inject(ToastService);
  private router   = inject(Router);
  private route    = inject(ActivatedRoute);

  form!: FormGroup;

  // ── Estados de UI ─────────────────────────────────────────────────────────
  loading      = signal(false);
  errorMessage = signal<string | null>(null);
  showPassword = signal(false);

  // URL de retorno tras login (si el guard redirigió)
  private returnUrl = '/';

  ngOnInit(): void {
    // Si ya está autenticado, ir al dashboard correspondiente
    if (this.auth.isAuthenticated()) {
      this.auth.redirectToDashboard();
      return;
    }

    this.returnUrl = this.route.snapshot.queryParamMap.get('returnUrl') ?? '';

    this.form = this.fb.group({
      correo:     ['', [Validators.required, Validators.email]],
      password:   ['', [Validators.required, Validators.minLength(6)]],
      rememberMe: [false],
    });
  }

  // ── Getters ───────────────────────────────────────────────────────────────
  get correo()   { return this.form.get('correo')!;   }
  get password() { return this.form.get('password')!; }

  // ── Envío ─────────────────────────────────────────────────────────────────
  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.loading.set(true);
    this.errorMessage.set(null);

    const { correo, password, rememberMe } = this.form.getRawValue();

    this.auth.login({ correo, password }, rememberMe).subscribe({
      next: () => {
        this.loading.set(false);
        this.toast.success('Sesión iniciada correctamente.');
        // Redirigir a returnUrl si existe, de lo contrario al dashboard por rol
        if (this.returnUrl) {
          this.router.navigate([this.returnUrl]);
        } else {
          this.auth.redirectToDashboard();
        }
      },
      error: (msg: string) => {
        this.loading.set(false);
        this.errorMessage.set(msg);
        this.toast.error('Error al iniciar sesión.');
      },
    });
  }

  togglePassword(): void {
    this.showPassword.update((v) => !v);
  }
}
