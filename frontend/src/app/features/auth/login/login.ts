import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../auth.service';

@Component({
  imports: [RouterLink, FormsModule],
  selector: 'app-login',
  styleUrl: './login.scss',
  templateUrl: './login.html',
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly correo = signal('');
  readonly password = signal('');
  readonly cargando = signal(false);
  readonly error = signal('');

  ingresar(): void {
    if (this.cargando()) return;
    this.error.set('');

    if (!this.correo().trim() || this.password().length < 8) {
      this.error.set('Ingresa tu correo y una contraseña de al menos 8 caracteres.');
      return;
    }

    this.cargando.set(true);
    this.auth.login(this.correo().trim(), this.password()).subscribe({
      next: (respuesta) => {
        this.cargando.set(false);
        const destino = ['platform_admin', 'moderator'].includes(respuesta.rol) ? '/admin' : '/dashboard';
        void this.router.navigate([destino]);
      },
      error: (err: HttpErrorResponse) => {
        this.cargando.set(false);
        const detalle = typeof err.error?.detail === 'string' ? err.error.detail : null;
        this.error.set(detalle ?? 'Credenciales incorrectas o cuenta no activa. Verifica tus datos e intenta de nuevo.');
      },
    });
  }
}
