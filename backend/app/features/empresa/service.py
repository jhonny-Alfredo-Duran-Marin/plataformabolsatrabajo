import uuid

from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundException
from app.features.empresa.repository import EmpresaRepository
from app.features.empresa.schema import EmpresaResponse
from app.models.empresa import Company
from app.shared.email_service import EmailService

_MAPA_ESTADO = {
    "pending": "PENDIENTE",
    "in_review": "PENDIENTE",
    "verified": "VERIFICADA",
    "rejected": "RECHAZADA",
}


def _a_dto(empresa: Company) -> EmpresaResponse:
    estado = _MAPA_ESTADO.get(empresa.verification_status)
    if empresa.account_status == "suspended":
        estado = "SUSPENDIDA"
    return EmpresaResponse(
        id=empresa.id,
        razon_social=empresa.trade_name or empresa.legal_name,
        nit=empresa.tax_id,
        sector=empresa.sector.name if empresa.sector else None,
        estado_verificacion=estado or "PENDIENTE",
    )


class EmpresaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EmpresaRepository(db)
        self.email_service = EmailService()

    def listar_pendientes(self) -> list[EmpresaResponse]:
        return [_a_dto(empresa) for empresa in self.repo.listar_pendientes()]

    def decidir(self, empresa_id: uuid.UUID | str, aprobado: bool, motivo_rechazo: str | None) -> EmpresaResponse:
        empresa = self._obtener(empresa_id)
        empresa.verification_status = "verified" if aprobado else "rejected"
        if not aprobado:
            self.email_service.enviar(
                empresa.contact_email or "",
                "Solicitud de registro rechazada",
                f"Tu solicitud fue rechazada. Motivo: {motivo_rechazo or 'no especificado'}.",
            )
        else:
            self.email_service.enviar(
                empresa.contact_email or "",
                "Empresa autorizada",
                "Tu empresa fue autorizada para publicar vacantes en la plataforma.",
            )
        self.db.commit()
        return _a_dto(empresa)

    def suspender(self, empresa_id: uuid.UUID | str, motivo: str) -> EmpresaResponse:
        empresa = self._obtener(empresa_id)
        empresa.account_status = "suspended"
        self.db.commit()
        return _a_dto(empresa)

    def _obtener(self, empresa_id: uuid.UUID | str) -> Company:
        empresa = self.repo.obtener_por_id(empresa_id)
        if empresa is None:
            raise ResourceNotFoundException("No se encontró la empresa.")
        return empresa
