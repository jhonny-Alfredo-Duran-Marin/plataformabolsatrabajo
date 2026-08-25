import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Empresa } from '../../../core/models/empresa.models';
import { EmpresaService } from '../../../core/services/empresa.service';

@Component({
  selector: 'app-empresas-gestion',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './empresas-gestion.component.html',
  styleUrl: './empresas-gestion.component.scss',
})
export class EmpresasGestionComponent implements OnInit {
  private readonly empresaService = inject(EmpresaService);

  empresas: Empresa[] = [];
  isLoading = false;
  errorMessage: string | null = null;
  toastMessage: string | null = null;

  // Filtros
  searchTerm = '';
  filtroEstado = 'TODAS'; // 'TODAS', 'ACTIVAS', 'INACTIVAS', 'PENDIENTES'

  // Modal de confirmación de eliminación lógica
  showDeleteModal = false;
  empresaParaDesactivar: Empresa | null = null;
  isProcessingAction = false;

  ngOnInit(): void {
    this.cargarEmpresas();
  }

  cargarEmpresas(): void {
    this.isLoading = true;
    this.errorMessage = null;

    this.empresaService.listarEmpresas(true).subscribe({
      next: (data) => {
        this.empresas = data;
        this.isLoading = false;
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage =
          'No se pudieron cargar las empresas. Verifica la conexión con el servidor.';
      },
    });
  }

  get empresasFiltradas(): Empresa[] {
    return this.empresas.filter((emp) => {
      const matchSearch =
        emp.razon_social.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        emp.nit.toLowerCase().includes(this.searchTerm.toLowerCase()) ||
        (emp.sector && emp.sector.toLowerCase().includes(this.searchTerm.toLowerCase())) ||
        (emp.representante_legal &&
          emp.representante_legal.toLowerCase().includes(this.searchTerm.toLowerCase()));

      if (!matchSearch) return false;

      if (this.filtroEstado === 'ACTIVAS') return emp.activo;
      if (this.filtroEstado === 'INACTIVAS') return !emp.activo;
      if (this.filtroEstado === 'PENDIENTES')
        return emp.estado_verificacion === 'PENDIENTE';

      return true;
    });
  }

  toggleNotificaciones(empresa: Empresa, event: Event): void {
    const input = event.target as HTMLInputElement;
    const nuevoValor = input.checked;

    this.empresaService
      .actualizarConfiguracion(empresa.id, { notificaciones_activas: nuevoValor })
      .subscribe({
        next: (updated) => {
          empresa.notificaciones_activas = updated.notificaciones_activas;
          this.showToast(
            `Notificaciones ${nuevoValor ? 'activadas' : 'desactivadas'} para "${empresa.razon_social}".`
          );
        },
        error: () => {
          input.checked = !nuevoValor; // revertir en caso de error
          this.showToast('Error al actualizar permisos de notificación.', true);
        },
      });
  }

  togglePostulaciones(empresa: Empresa, event: Event): void {
    const input = event.target as HTMLInputElement;
    const nuevoValor = input.checked;

    this.empresaService
      .actualizarConfiguracion(empresa.id, { postulaciones_activas: nuevoValor })
      .subscribe({
        next: (updated) => {
          empresa.postulaciones_activas = updated.postulaciones_activas;
          this.showToast(
            `Postulaciones ${nuevoValor ? 'habilitadas' : 'inhabilitadas'} para "${empresa.razon_social}".`
          );
        },
        error: () => {
          input.checked = !nuevoValor;
          this.showToast('Error al actualizar permisos de postulación.', true);
        },
      });
  }

  abrirModalBajaLogica(empresa: Empresa): void {
    this.empresaParaDesactivar = empresa;
    this.showDeleteModal = true;
  }

  cerrarModal(): void {
    this.showDeleteModal = false;
    this.empresaParaDesactivar = null;
  }

  confirmarBajaLogica(): void {
    if (!this.empresaParaDesactivar) return;

    this.isProcessingAction = true;
    const id = this.empresaParaDesactivar.id;
    const razon = this.empresaParaDesactivar.razon_social;

    this.empresaService.eliminarLogico(id).subscribe({
      next: (updated) => {
        this.isProcessingAction = false;
        this.cerrarModal();
        const index = this.empresas.findIndex((e) => e.id === id);
        if (index !== -1) {
          this.empresas[index] = updated;
        }
        this.showToast(`Empresa "${razon}" dada de baja lógicamente (historial conservado).`);
      },
      error: () => {
        this.isProcessingAction = false;
        this.showToast('Error al dar de baja la empresa.', true);
      },
    });
  }

  restaurarEmpresa(empresa: Empresa): void {
    this.empresaService.restaurar(empresa.id).subscribe({
      next: (updated) => {
        const index = this.empresas.findIndex((e) => e.id === empresa.id);
        if (index !== -1) {
          this.empresas[index] = updated;
        }
        this.showToast(`Empresa "${empresa.razon_social}" reactivada con éxito.`);
      },
      error: () => {
        this.showToast('Error al reactivar la empresa.', true);
      },
    });
  }

  private showToast(msg: string, isError = false): void {
    this.toastMessage = msg;
    setTimeout(() => {
      if (this.toastMessage === msg) {
        this.toastMessage = null;
      }
    }, 4000);
  }
}

