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


class ValidacionEgresadoDecisionRequest(BaseModel):
    aprobado: bool
    motivo_rechazo: str | None = None


class VisibilidadPerfilRequest(BaseModel):
    perfil_oculto: bool
    secciones_visibles: dict[str, bool]
