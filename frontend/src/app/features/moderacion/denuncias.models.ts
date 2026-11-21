import { HttpErrorResponse } from '@angular/common/http';

/** HU-22: denuncia de ofertas. Los valores coinciden con moderation_report.category. */
export type CategoriaDenuncia =
  'fraud' | 'inappropriate' | 'spam' | 'fake_information' | 'discrimination' | 'other';
export type DecisionDenuncia = 'mantener' | 'suspender' | 'eliminar';

/** Caracteres de detalle para que una denuncia cuente para ocultar la oferta (igual que el backend). */
export const MINIMO_FUNDAMENTO = 20;

export const CATEGORIAS_DENUNCIA: { valor: CategoriaDenuncia; etiqueta: string; ayuda: string }[] =
  [
    {
      valor: 'fraud',
      etiqueta: 'Fraude o estafa',
      ayuda: 'Piden dinero, datos bancarios o un pago para postular.',
    },
    {
      valor: 'fake_information',
      etiqueta: 'Información falsa',
      ayuda: 'La empresa, el sueldo o el puesto no son reales.',
    },
    {
      valor: 'discrimination',
      etiqueta: 'Discriminación',
      ayuda: 'Excluye por género, edad, origen u otra condición.',
    },
    {
      valor: 'inappropriate',
      etiqueta: 'Contenido inapropiado',
      ayuda: 'Lenguaje ofensivo o contenido que no es una oferta.',
    },
    {
      valor: 'spam',
      etiqueta: 'Spam o publicidad',
      ayuda: 'Promociona cursos, productos o es una oferta repetida.',
    },
    { valor: 'other', etiqueta: 'Otro motivo', ayuda: 'Contanos qué pasó.' },
  ];

export function etiquetaCategoria(valor: string): string {
  return CATEGORIAS_DENUNCIA.find((c) => c.valor === valor)?.etiqueta ?? valor;
}

export interface DenunciaCreada {
  id: string;
  cuenta_para_umbral: boolean;
  mensaje: string;
}

export interface MiDenuncia {
  denunciada: boolean;
  fecha: string | null;
}

export interface DenunciaItem {
  id: string;
  categoria: CategoriaDenuncia;
  descripcion: string | null;
  cuenta_para_umbral: boolean;
  denunciante_nombre: string;
  denunciante_correo: string;
  created_at: string;
}

export interface VacanteDenunciada {
  vacante_id: string;
  titulo: string;
  ciudad: string | null;
  estado_vacante: string;
  empresa_id: string;
  empresa_nombre: string;
  oculta: boolean;
  denuncias_que_cuentan: number;
  ultima_denuncia_at: string;
  denuncias: DenunciaItem[];
}

export interface DenunciasPendientes {
  items: VacanteDenunciada[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  umbral: number;
}

export interface ResolucionDenuncia {
  vacante_id: string;
  decision: DecisionDenuncia;
  estado_vacante: string;
  denuncias_cerradas: number;
}

/** El backend responde `detail` como texto o, en errores de validación, como lista. */
export function mensajeDeError(err: HttpErrorResponse, porDefecto: string): string {
  const detalle = err.error?.detail;
  if (typeof detalle === 'string') return detalle;
  if (Array.isArray(detalle) && detalle[0]?.msg)
    return String(detalle[0].msg).replace(/^Value error, /, '');
  return porDefecto;
}
