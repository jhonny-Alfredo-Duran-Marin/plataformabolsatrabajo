from sqlalchemy.orm import Session

from app.common.exceptions import ResourceNotFoundException
from app.models.empresa import Empresa
from app.models.enums import EstadoVerificacionEmpresa
from app.repositories.empresa_repository import EmpresaRepository
from app.services.email_service import EmailService


class EmpresaService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = EmpresaRepository(db)
        self.email_service = EmailService()

    def listar_pendientes(self) -> list[Empresa]:
        return self.repo.listar_pendientes()

    def decidir(self, empresa_id: int, aprobado: bool, motivo_rechazo: str | None) -> Empresa:
        empresa = self._obtener(empresa_id)
        empresa.estado_verificacion = (
            EstadoVerificacionEmpresa.VERIFICADA if aprobado else EstadoVerificacionEmpresa.RECHAZADA
        )
        empresa.motivo_rechazo = None if aprobado else motivo_rechazo
        self.db.commit()
        return empresa

    def suspender(self, empresa_id: int, motivo: str) -> Empresa:
        empresa = self._obtener(empresa_id)
        empresa.estado_verificacion = EstadoVerificacionEmpresa.SUSPENDIDA
        empresa.motivo_rechazo = motivo
        self.db.commit()
        return empresa

    def _obtener(self, empresa_id: int) -> Empresa:
        empresa = self.repo.obtener_por_id(empresa_id)
        if empresa is None:
            raise ResourceNotFoundException("No se encontró la empresa.")
        return empresa
