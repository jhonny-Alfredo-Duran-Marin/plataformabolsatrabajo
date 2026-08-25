import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.empresa import Company, CompanyMember


class EmpresaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_por_usuario_id(self, usuario_id: uuid.UUID | str) -> Company | None:
        stmt = (
            select(Company)
            .join(CompanyMember, CompanyMember.company_id == Company.id)
            .where(CompanyMember.user_id == usuario_id)
        )
        return self.db.scalar(stmt)

    def obtener_por_id(self, empresa_id: uuid.UUID | str) -> Company | None:
        return self.db.get(Company, empresa_id)

    def existe_nit(self, nit: str) -> bool:
        return self.db.scalar(select(Company.id).where(Company.tax_id == nit)) is not None

    def crear(self, empresa: Company) -> Company:
        self.db.add(empresa)
        self.db.flush()
        return empresa

    def listar_pendientes(self) -> list[Company]:
        stmt = (
            select(Company)
            .where(Company.deleted_at.is_(None))
            .where(Company.verification_status == "pending")
            .order_by(Company.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def listar_todas(self, incluir_inactivas: bool = False) -> list[Company]:
        stmt = select(Company).order_by(Company.created_at.desc())
        if not incluir_inactivas:
            stmt = stmt.where(Company.deleted_at.is_(None))
        return list(self.db.scalars(stmt))
