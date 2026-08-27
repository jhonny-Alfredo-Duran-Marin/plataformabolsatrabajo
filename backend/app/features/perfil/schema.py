import uuid
from datetime import date

from pydantic import BaseModel


class PerfilEgresadoResponse(BaseModel):
    id: uuid.UUID
    usuario_id: uuid.UUID
    nombres: str
    apellidos: str
    ci: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    fecha_nacimiento: date | None = None
    carrera_id: uuid.UUID | None = None
    anio_egreso: int | None = None
    matricula: str | None = None
    disponibilidad: str | None = None
    estado_validacion: str  # PENDIENTE | APROBADO | RECHAZADO (mapeado desde verification_status)
    porcentaje_completitud: int
    perfil_oculto: bool
    visibilidad_secciones: str = "{}"
    ciudad: str | None = None
    titulo_profesional: str | None = None
    resumen_profesional: str | None = None


class PerfilEgresadoUpdateRequest(BaseModel):
    telefono: str | None = None
    direccion: str | None = None  # sin columna en el esquema nuevo; se acepta y se ignora
    fecha_nacimiento: date | None = None  # ídem
    estado_laboral: str | None = None
    url_redes_profesionales: str | None = None
    disponibilidad: str | None = None
    titulo_profesional: str | None = None
    resumen_profesional: str | None = None
    ciudad: str | None = None
    carrera_id: uuid.UUID | None = None
    anio_egreso: int | None = None
    matricula: str | None = None


class FormacionRequest(BaseModel):
    institucion: str
    programa: str
    estado_academico: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class FormacionResponse(FormacionRequest):
    id: uuid.UUID


class ExperienciaRequest(BaseModel):
    empresa: str
    cargo: str
    descripcion: str | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class ExperienciaResponse(ExperienciaRequest):
    id: uuid.UUID


class IdiomaRequest(BaseModel):
    idioma: str
    nivel: str = "basico"


class IdiomaResponse(IdiomaRequest):
    id: uuid.UUID


class CertificacionRequest(BaseModel):
    nombre: str
    entidad_emisora: str | None = None
    fecha_obtencion: date | None = None


class CertificacionResponse(CertificacionRequest):
    id: uuid.UUID


class HabilidadesRequest(BaseModel):
    habilidades: list[str]


class HabilidadResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    categoria: str | None = None


class ValidacionEgresadoDecisionRequest(BaseModel):
    aprobado: bool
    motivo_rechazo: str | None = None


class VisibilidadPerfilRequest(BaseModel):
    perfil_oculto: bool
    secciones_visibles: dict[str, bool]
