from datetime import datetime

from pydantic import BaseModel


class AuditoriaLogResponse(BaseModel):
    id: int
    usuario_id: int | None
    ip: str | None
    modulo: str
    accion: str
    detalles: str | None
    resultado: bool
    fecha: datetime

    model_config = {"from_attributes": True}
