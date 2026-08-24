import uuid
from datetime import datetime

from pydantic import BaseModel


class BitacoraLogResponse(BaseModel):
    id: uuid.UUID
    usuario_id: uuid.UUID | None = None
    ip: str | None = None
    modulo: str
    accion: str
    detalles: str | None = None
    resultado: bool
    fecha: datetime

    model_config = {"from_attributes": True}
