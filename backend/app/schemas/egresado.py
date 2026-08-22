from datetime import date

from pydantic import BaseModel

from app.models.enums import EstadoValidacionEgresado


class PerfilEgresadoResponse(BaseModel):
    id: int
    usuario_id: int
    nombres: str
    apellidos: str
    ci: str
    telefono: str | None
    direccion: str | None
    fecha_nacimiento: date | None
    carrera_id: int | None
    anio_egreso: int | None
    estado_validacion: EstadoValidacionEgresado
    porcentaje_completitud: int
    perfil_oculto: bool

    model_config = {"from_attributes": True}


class PerfilEgresadoUpdateRequest(BaseModel):
    telefono: str | None = None
    direccion: str | None = None
    fecha_nacimiento: date | None = None
    estado_laboral: str | None = None
    url_redes_profesionales: str | None = None
    disponibilidad: str | None = None


class ValidacionEgresadoDecisionRequest(BaseModel):
    aprobado: bool
    motivo_rechazo: str | None = None


class VisibilidadPerfilRequest(BaseModel):
    perfil_oculto: bool
    secciones_visibles: dict[str, bool]
