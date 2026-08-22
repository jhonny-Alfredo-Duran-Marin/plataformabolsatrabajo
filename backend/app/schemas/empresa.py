from pydantic import BaseModel

from app.models.enums import EstadoVerificacionEmpresa


class EmpresaResponse(BaseModel):
    id: int
    usuario_id: int
    razon_social: str
    nit: str
    sector: str | None
    estado_verificacion: EstadoVerificacionEmpresa

    model_config = {"from_attributes": True}


class DecisionEmpresaRequest(BaseModel):
    aprobado: bool
    motivo_rechazo: str | None = None


class SuspensionEmpresaRequest(BaseModel):
    motivo: str
