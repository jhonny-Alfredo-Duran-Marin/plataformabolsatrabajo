import uuid
from datetime import date, datetime, time
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.candidato import CandidateProfile
from app.models.empresa import Company
from app.models.postulacion import (
    Application,
    ApplicationStageHistory,
    ApplicationStatusHistory,
)
from app.models.vacante import JobPosting, JobSelectionStage, JobSkill


class PostulacionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_perfil_candidato(self, user_id: uuid.UUID) -> CandidateProfile | None:
        stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        return self.db.scalar(stmt)

    def listar_postulaciones_candidato(
        self,
        candidate_id: uuid.UUID,
        estado: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        busqueda: str | None = None,
    ) -> list[Application]:
        stmt = (
            select(Application)
            .join(JobPosting, Application.job_id == JobPosting.id)
            .join(Company, JobPosting.company_id == Company.id)
            .options(
                joinedload(Application.job_posting).joinedload(JobPosting.company),
                joinedload(Application.current_stage),
            )
            .where(Application.candidate_id == candidate_id)
        )

        if estado and estado.strip():
            estado_clean = estado.strip().lower()
            if estado_clean == "in_review" or estado_clean == "screening":
                stmt = stmt.where(Application.current_status.in_(["screening", "in_review"]))
            else:
                stmt = stmt.where(Application.current_status == estado_clean)

        if fecha_desde:
            dt_desde = datetime.combine(fecha_desde, time.min)
            stmt = stmt.where(Application.applied_at >= dt_desde)

        if fecha_hasta:
            dt_hasta = datetime.combine(fecha_hasta, time.max)
            stmt = stmt.where(Application.applied_at <= dt_hasta)

        if busqueda and busqueda.strip():
            query_str = f"%{busqueda.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(JobPosting.title).like(query_str),
                    func.lower(Company.legal_name).like(query_str),
                    func.lower(Company.trade_name).like(query_str),
                )
            )

        stmt = stmt.order_by(Application.applied_at.desc())
        return list(self.db.scalars(stmt).all())

    def obtener_por_id_y_candidato(
        self, application_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Application | None:
        stmt = (
            select(Application)
            .options(
                joinedload(Application.job_posting).joinedload(JobPosting.company).joinedload(Company.sector),
                joinedload(Application.current_stage),
                selectinload(Application.status_history),
                selectinload(Application.stage_history).joinedload(ApplicationStageHistory.stage),
            )
            .where(
                Application.id == application_id,
                Application.candidate_id == candidate_id,
            )
        )
        app = self.db.scalar(stmt)
        if app and app.job_posting:
            # Asegurar carga de habilidades de la vacante
            self.db.refresh(app.job_posting, ["skills"])
            for js in app.job_posting.skills:
                self.db.refresh(js, ["skill"])
        return app

    def registrar_cambio_estado(
        self,
        application: Application,
        nuevo_estado: str,
        user_id: uuid.UUID | None,
        motivo: str | None = None,
    ) -> ApplicationStatusHistory:
        historial = ApplicationStatusHistory(
            application_id=application.id,
            from_status=application.current_status,
            to_status=nuevo_estado,
            changed_by=user_id,
            reason=motivo,
        )
        self.db.add(historial)
        return historial
