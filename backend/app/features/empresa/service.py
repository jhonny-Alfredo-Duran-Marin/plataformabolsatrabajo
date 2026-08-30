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

# NOTA sobre limitaciones del esquema real (ver también app/models/empresa.py):
# - notifications_enabled / applications_enabled: no existen como columnas en `company`
#   ni en ninguna otra tabla del esquema real. No hay dónde persistirlas sin agregar
#   columnas (regla de oro: no tocar el esquema de Supabase). Se aceptan los cambios
#   vía el endpoint de configuración y se devuelven en la respuesta, pero NO sobreviven
#   a un reinicio del proceso (se guardan solo en memoria, por instancia de Company
#   dentro de la sesión actual). Limitación documentada y aceptada para esta pasada.
# - legal_representative: tampoco existe columna; se acepta en el registro y se ignora.
# - "baja lógica" (deleted_at): no existe; se reutiliza account_status='suspended'
#   como equivalente más cercano, por lo que eliminar_logico/restaurar quedan
#   funcionalmente equivalentes a suspender/reactivar.


def _a_dto(empresa: Company, motivo_rechazo: str | None) -> EmpresaResponse:
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
        representante_legal=None,
        estado_verificacion=estado or "PENDIENTE",
        motivo_rechazo=motivo_rechazo,
        notificaciones_activas=getattr(empresa, "_notificaciones_activas", True),
        postulaciones_activas=getattr(empresa, "_postulaciones_activas", True),
        activo=empresa.account_status != "suspended",
        fecha_registro=empresa.created_at,
        fecha_eliminacion=None,
    )


class EmpresaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EmpresaRepository(db)
        self.email_service = EmailService()

    def _dto_con_motivo(self, empresa: Company) -> EmpresaResponse:
        return _a_dto(empresa, self.repo.ultimo_motivo_rechazo(empresa.id))

    def listar_pendientes(self) -> list[EmpresaResponse]:
        return [self._dto_con_motivo(empresa) for empresa in self.repo.listar_pendientes()]

    def listar_todas(self, incluir_inactivas: bool = False) -> list[EmpresaResponse]:
        return [self._dto_con_motivo(empresa) for empresa in self.repo.listar_todas(incluir_inactivas=incluir_inactivas)]

    def decidir(self, empresa_id: uuid.UUID | str, aprobado: bool, motivo_rechazo: str | None) -> EmpresaResponse:
        empresa = self._obtener(empresa_id)
        empresa.verification_status = "verified" if aprobado else "rejected"
        self.repo.registrar_verificacion(
            empresa.id,
            status="verified" if aprobado else "rejected",
            rejection_reason=None if aprobado else (motivo_rechazo or "no especificado"),
        )
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
        return self._dto_con_motivo(empresa)

    def suspender(self, empresa_id: uuid.UUID | str, motivo: str) -> EmpresaResponse:
        empresa = self._obtener(empresa_id)
        empresa.account_status = "suspended"
        # company_verification.status no admite 'suspended' (CHECK), se usa 'rejected'
        # como estado de historial más cercano junto con una nota aclaratoria.
        self.repo.registrar_verificacion(
            empresa.id, status="rejected", rejection_reason=motivo or "no especificado", notes="Suspensión de cuenta"
        )
        self.email_service.enviar(
            empresa.contact_email or "",
            "Empresa suspendida",
            f"Tu empresa fue suspendida de la plataforma. Motivo: {motivo or 'no especificado'}.",
        )
        self.db.commit()
        return self._dto_con_motivo(empresa)

    def actualizar_configuracion(
        self,
        empresa_id: uuid.UUID | str,
        notificaciones_activas: bool | None = None,
        postulaciones_activas: bool | None = None,
    ) -> EmpresaResponse:
        empresa = self._obtener(empresa_id)
        # Ver nota de limitaciones arriba: no hay columna para persistir esto en el
        # esquema real, se guarda como atributo en memoria del objeto de esta sesión.
        if notificaciones_activas is not None:
            empresa._notificaciones_activas = notificaciones_activas  # type: ignore[attr-defined]
        if postulaciones_activas is not None:
            empresa._postulaciones_activas = postulaciones_activas  # type: ignore[attr-defined]
        self.db.commit()
        return self._dto_con_motivo(empresa)

    def eliminar_logico(self, empresa_id: uuid.UUID | str) -> EmpresaResponse:
        """Baja lógica: el esquema real no tiene deleted_at, se modela como suspensión."""
        empresa = self._obtener(empresa_id)
        empresa.account_status = "suspended"
        self.repo.registrar_verificacion(
            empresa.id, status="rejected", rejection_reason="Baja lógica de la cuenta", notes="Eliminación lógica"
        )
        self.db.commit()
        return self._dto_con_motivo(empresa)

    def restaurar(self, empresa_id: uuid.UUID | str) -> EmpresaResponse:
        """Restaura una empresa suspendida/dada de baja lógicamente."""
        empresa = self._obtener(empresa_id)
        if empresa.account_status == "suspended":
            empresa.account_status = "active"
            self.repo.registrar_verificacion(empresa.id, status="verified", notes="Reactivación de cuenta")
            self.email_service.enviar(
                empresa.contact_email or "",
                "Empresa reactivada",
                "Tu empresa fue reactivada y puede volver a operar en la plataforma.",
            )
        self.db.commit()
        return self._dto_con_motivo(empresa)

    def _obtener(self, empresa_id: uuid.UUID | str) -> Company:
        empresa = self.repo.obtener_por_id(empresa_id)
        if empresa is None:
            raise ResourceNotFoundException("No se encontró la empresa.")
        return empresa
