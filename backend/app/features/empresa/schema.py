import uuid
from datetime import datetime

from pydantic import BaseModel


class EmpresaResponse(BaseModel):
    id: uuid.UUID
    usuario_id: uuid.UUID | None = None
    razon_social: str
    nit: str
    sector: str | None = None
    tamanio: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    sitio_web: str | None = None
    descripcion: str | None = None
    representante_legal: str | None = None
    estado_verificacion: str  # PENDIENTE | VERIFICADA | RECHAZADA | SUSPENDIDA (mapeado)
    motivo_rechazo: str | None = None
    notificaciones_activas: bool = True
    postulaciones_activas: bool = True
    activo: bool = True
    fecha_registro: datetime | None = None
    fecha_eliminacion: datetime | None = None

    model_config = {"from_attributes": True}


class DecisionEmpresaRequest(BaseModel):
    aprobado: bool
    motivo_rechazo: str | None = None


class SuspensionEmpresaRequest(BaseModel):
    motivo: str


class ConfiguracionEmpresaRequest(BaseModel):
    notificaciones_activas: bool | None = None
    postulaciones_activas: bool | None = None
