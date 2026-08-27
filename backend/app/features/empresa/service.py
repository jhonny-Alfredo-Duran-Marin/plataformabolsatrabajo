import uuid
from datetime import datetime, timezone

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
        tamanio=empresa.company_size,
        direccion=empresa.address,
        telefono=empresa.phone,
        sitio_web=empresa.website,
        descripcion=empresa.description,
        representante_legal=empresa.legal_representative,
        estado_verificacion=estado or "PENDIENTE",
        motivo_rechazo=empresa.rejection_reason,
        notificaciones_activas=empresa.notifications_enabled,
        postulaciones_activas=empresa.applications_enabled,
        activo=empresa.deleted_at is None,
        fecha_registro=empresa.created_at,
        fecha_eliminacion=empresa.deleted_at,
    )


class EmpresaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EmpresaRepository(db)
        self.email_service = EmailService()

    def listar_pendientes(self) -> list[EmpresaResponse]:
        return [_a_dto(empresa) for empresa in self.repo.listar_pendientes()]

    def listar_todas(self, incluir_inactivas: bool = False) -> list[EmpresaResponse]:
        return [_a_dto(empresa) for empresa in self.repo.listar_todas(incluir_inactivas=incluir_inactivas)]

    def decidir(self, empresa_id: uuid.UUID | str, aprobado: bool, motivo_rechazo: str | None) -> EmpresaResponse:
        empresa = self._obtener(empresa_id)
        empresa.verification_status = "verified" if aprobado else "rejected"
        empresa.rejection_reason = None if aprobado else motivo_rechazo
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
        empresa.rejection_reason = motivo
        self.email_service.enviar(
            empresa.contact_email or "",
            "Empresa suspendida",
            f"Tu empresa fue suspendida de la plataforma. Motivo: {motivo or 'no especificado'}.",
        )
        self.db.commit()
        return _a_dto(empresa)

    def actualizar_configuracion(
        self,
        empresa_id: uuid.UUID | str,
        notificaciones_activas: bool | None = None,
        postulaciones_activas: bool | None = None,
    ) -> EmpresaResponse:
        empresa = self._obtener(empresa_id)
        if notificaciones_activas is not None:
            empresa.notifications_enabled = notificaciones_activas
        if postulaciones_activas is not None:
            empresa.applications_enabled = postulaciones_activas
        self.db.commit()
        return _a_dto(empresa)

    def eliminar_logico(self, empresa_id: uuid.UUID | str) -> EmpresaResponse:
        """Baja lógica (soft delete): preserva integridad histórica y auditoría."""
        empresa = self._obtener(empresa_id)
        empresa.deleted_at = datetime.now(timezone.utc)
        self.db.commit()
        return _a_dto(empresa)

    def restaurar(self, empresa_id: uuid.UUID | str) -> EmpresaResponse:
        """Restaura una empresa dada de baja lógicamente o revierte su suspensión."""
        empresa = self._obtener(empresa_id)
        empresa.deleted_at = None
        if empresa.account_status == "suspended":
            empresa.account_status = "active"
            empresa.rejection_reason = None
            self.email_service.enviar(
                empresa.contact_email or "",
                "Empresa reactivada",
                "Tu empresa fue reactivada y puede volver a operar en la plataforma.",
            )
        self.db.commit()
        return _a_dto(empresa)

    def _obtener(self, empresa_id: uuid.UUID | str) -> Company:
        empresa = self.repo.obtener_por_id(empresa_id)
        if empresa is None:
            raise ResourceNotFoundException("No se encontró la empresa.")
        return empresa
