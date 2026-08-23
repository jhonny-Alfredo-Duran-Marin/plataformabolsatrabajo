import { Injectable, signal } from '@angular/core';

const TOKEN_STORAGE_KEY = 'egresa_admin_token';

// TODO: reemplazar por el flujo real de login/guard de rol cuando exista.
@Injectable({ providedIn: 'root' })
export class AdminTokenService {
  readonly token = signal(localStorage.getItem(TOKEN_STORAGE_KEY) ?? '');

  guardar(token: string): void {
    this.token.set(token);
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  }
}
