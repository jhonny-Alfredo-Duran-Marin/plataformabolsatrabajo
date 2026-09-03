import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.empresa import Company, CompanyMember, CompanyVerification


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
            .options(selectinload(Company.sector))
            .where(Company.verification_status == "pending")
            .order_by(Company.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def listar_todas(self, incluir_inactivas: bool = False) -> list[Company]:
        stmt = select(Company).options(selectinload(Company.sector)).order_by(Company.created_at.desc())
        if not incluir_inactivas:
            stmt = stmt.where(Company.account_status != "suspended")
        return list(self.db.scalars(stmt))

    # --- Historial de verificación/autorización (motivo de rechazo/suspensión real) ---
    def registrar_verificacion(
        self,
        company_id: uuid.UUID,
        status: str,
        rejection_reason: str | None = None,
        notes: str | None = None,
        reviewed_by: uuid.UUID | None = None,
    ) -> CompanyVerification:
        registro = CompanyVerification(
            company_id=company_id,
            status=status,
            document_key="sin-documento",  # no se maneja upload de documento en esta etapa
            rejection_reason=rejection_reason,
            notes=notes,
            reviewed_by=reviewed_by,
        )
        self.db.add(registro)
        self.db.flush()
        return registro

    def ultimo_motivo_rechazo(self, company_id: uuid.UUID) -> str | None:
        stmt = (
            select(CompanyVerification.rejection_reason)
            .where(
                CompanyVerification.company_id == company_id,
                CompanyVerification.rejection_reason.is_not(None),
            )
            .order_by(CompanyVerification.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def ultimos_motivos_rechazo(self, company_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        """Versión batch de ultimo_motivo_rechazo: una sola query para todas las
        empresas en vez de una por empresa (evita N+1 al listar)."""
        if not company_ids:
            return {}
        rn = func.row_number().over(
            partition_by=CompanyVerification.company_id,
            order_by=CompanyVerification.created_at.desc(),
        ).label("rn")
        subq = (
            select(
                CompanyVerification.company_id,
                CompanyVerification.rejection_reason,
                rn,
            )
            .where(
                CompanyVerification.company_id.in_(company_ids),
                CompanyVerification.rejection_reason.is_not(None),
            )
            .subquery()
        )
        stmt = select(subq.c.company_id, subq.c.rejection_reason).where(subq.c.rn == 1)
        return {row.company_id: row.rejection_reason for row in self.db.execute(stmt)}
