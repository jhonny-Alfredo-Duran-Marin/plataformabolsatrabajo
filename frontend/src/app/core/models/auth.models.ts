export interface RegistroEmpresaRequest {
  razon_social: string;
  nit: string;
  correo: string;
  password: string;
  sector?: string;
  tamanio?: string;
  direccion?: string;
  telefono?: string;
  sitio_web?: string;
  descripcion?: string;
  representante_legal?: string;
}

export interface MessageResponse {
  detail: string;
}

export interface ApiErrorResponse {
  detail?: string | Array<{ loc: (string | number)[]; msg: string; type: string }>;
}

