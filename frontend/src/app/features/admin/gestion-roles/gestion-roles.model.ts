export type RolSistema = 'candidate' | 'moderator' | 'platform_admin';

export const ETIQUETAS_ROL: Record<string, string> = {
  candidate: 'Egresado',
  moderator: 'Moderador',
  platform_admin: 'Administrador universitario',
};

export interface Rol {
  id: string;
  nombre: string;
  descripcion: string | null;
}

export interface UsuarioAdmin {
  id: string;
  correo: string;
  estado: string;
  fecha_registro: string;
  ultimo_acceso: string | null;
  roles: string[];
  es_miembro_empresa: boolean;
}

export interface AsignarRolRespuesta {
  usuario: UsuarioAdmin;
  rol_anterior: string | null;
  detalle: string;
}
