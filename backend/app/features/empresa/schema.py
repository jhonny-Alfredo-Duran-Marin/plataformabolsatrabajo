import uuid

from pydantic import BaseModel


class EmpresaResponse(BaseModel):
    id: uuid.UUID
    usuario_id: uuid.UUID | None = None
    razon_social: str
    nit: str
    sector: str | None = None
    estado_verificacion: str  # PENDIENTE | VERIFICADA | RECHAZADA | SUSPENDIDA (mapeado)

    model_config = {"from_attributes": True}


class DecisionEmpresaRequest(BaseModel):
    aprobado: bool
    motivo_rechazo: str | None = None


class SuspensionEmpresaRequest(BaseModel):
    motivo: str
