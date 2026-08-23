from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.enums import EstadoVerificacionEmpresa


class EmpresaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_por_usuario_id(self, usuario_id: int) -> Empresa | None:
        return self.db.scalar(select(Empresa).where(Empresa.usuario_id == usuario_id))

    def obtener_por_id(self, empresa_id: int) -> Empresa | None:
        return self.db.get(Empresa, empresa_id)

    def existe_nit(self, nit: str) -> bool:
        return self.db.scalar(select(Empresa).where(Empresa.nit == nit)) is not None

    def crear(self, empresa: Empresa) -> Empresa:
        self.db.add(empresa)
        self.db.flush()
        return empresa

    def listar_pendientes(self) -> list[Empresa]:
        stmt = select(Empresa).where(Empresa.estado_verificacion == EstadoVerificacionEmpresa.PENDIENTE)
        return list(self.db.scalars(stmt))
