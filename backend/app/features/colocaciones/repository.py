import uuid
from datetime import date

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.tenancy import condicion_institucion
from app.models.candidato import CandidateProfile
from app.models.colocacion import Placement
from app.models.empresa import Company
from app.models.institucion import Institution
from app.models.usuario import AppUser, Role, UserRole

_NOMBRE_EGRESADO = func.concat_ws(" ", CandidateProfile.first_name, CandidateProfile.last_name)


class ColocacionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _con_relaciones(self, stmt: Select) -> Select:
        return stmt.options(
            joinedload(Placement.candidate), joinedload(Placement.company), joinedload(Placement.institution)
        )

    def obtener(self, colocacion_id: uuid.UUID) -> Placement | None:
        return self.db.scalar(self._con_relaciones(select(Placement).where(Placement.id == colocacion_id)))

    def por_postulacion(self, postulacion_id: uuid.UUID) -> Placement | None:
        return self.db.scalar(select(Placement).where(Placement.application_id == postulacion_id))

    def existe_igual(
        self,
        candidate_id: uuid.UUID,
        cargo: str,
        fecha_inicio: date,
        company_id: uuid.UUID | None,
        company_name: str | None,
    ) -> bool:
        """Misma persona, cargo, fecha y empresa ya registrados (y no eliminados)."""
        stmt = select(Placement.id).where(
            Placement.candidate_id == candidate_id,
            func.lower(Placement.position_title) == cargo.lower(),
            Placement.start_date == fecha_inicio,
            Placement.status != "cancelled",
        )
        if company_id is not None:
            stmt = stmt.where(Placement.company_id == company_id)
        else:
            stmt = stmt.where(func.lower(Placement.company_name) == (company_name or "").lower())
        return self.db.scalar(stmt.limit(1)) is not None

    def listar(
        self,
        institution_id: uuid.UUID | None,
        page: int,
        page_size: int,
        estado: str | None,
        texto: str | None,
        desde: date | None,
        hasta: date | None,
    ) -> tuple[list[Placement], int]:
        filtros = []
        if institution_id is not None:
            filtros.append(Placement.institution_id == institution_id)
        # Sin estado se ven las vivas (sugeridas y confirmadas); las eliminadas se piden con estado=cancelled.
        filtros.append(Placement.status == estado if estado else Placement.status != "cancelled")
        if desde is not None:
            filtros.append(Placement.start_date >= desde)
        if hasta is not None:
            filtros.append(Placement.start_date <= hasta)

        base = (
            select(Placement.id)
            .join(CandidateProfile, CandidateProfile.id == Placement.candidate_id)
            .outerjoin(Company, Company.id == Placement.company_id)
            .where(*filtros)
        )
        if texto:
            patron = f"%{texto}%"
            base = base.where(
                or_(
                    _NOMBRE_EGRESADO.ilike(patron),
                    Placement.position_title.ilike(patron),
                    Placement.company_name.ilike(patron),
                    Company.trade_name.ilike(patron),
                    Company.legal_name.ilike(patron),
                )
            )
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        ids = self.db.scalars(
            base.order_by(
                case((Placement.status == "suggested", 0), else_=1),
                Placement.start_date.desc(),
                Placement.created_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        if not ids:
            return [], total
        filas = self.db.scalars(self._con_relaciones(select(Placement).where(Placement.id.in_(ids)))).unique().all()
        por_id = {f.id: f for f in filas}
        return [por_id[i] for i in ids], total

    def contar_sugeridas(self, institution_id: uuid.UUID | None) -> int:
        stmt = select(func.count()).select_from(Placement).where(Placement.status == "suggested")
        if institution_id is not None:
            stmt = stmt.where(Placement.institution_id == institution_id)
        return self.db.scalar(stmt) or 0

    def buscar_egresados(self, institution_id: uuid.UUID | None, texto: str | None, limite: int):
        stmt = (
            select(CandidateProfile.id, _NOMBRE_EGRESADO, AppUser.email, Institution.name)
            .join(AppUser, AppUser.id == CandidateProfile.user_id)
            .outerjoin(Institution, Institution.id == CandidateProfile.institution_id)
            .where(AppUser.account_status == "active")
        )
        if institution_id is not None:
            stmt = stmt.where(condicion_institucion(CandidateProfile.institution_id, institution_id))
        if texto:
            patron = f"%{texto}%"
            stmt = stmt.where(or_(_NOMBRE_EGRESADO.ilike(patron), AppUser.email.ilike(patron)))
        return self.db.execute(stmt.order_by(_NOMBRE_EGRESADO).limit(limite)).all()

    def buscar_empresas(self, texto: str | None, limite: int) -> list[Company]:
        stmt = select(Company).where(Company.account_status == "active")
        if texto:
            patron = f"%{texto}%"
            stmt = stmt.where(or_(Company.trade_name.ilike(patron), Company.legal_name.ilike(patron)))
        return list(
            self.db.scalars(stmt.order_by(func.coalesce(Company.trade_name, Company.legal_name)).limit(limite)).all()
        )

    def admins_de_institucion(self, institution_id: uuid.UUID) -> list[uuid.UUID]:
        return list(
            self.db.scalars(
                select(AppUser.id)
                .join(UserRole, UserRole.user_id == AppUser.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    Role.name == "platform_admin",
                    AppUser.institution_id == institution_id,
                    AppUser.account_status == "active",
                )
                .distinct()
            ).all()
        )
