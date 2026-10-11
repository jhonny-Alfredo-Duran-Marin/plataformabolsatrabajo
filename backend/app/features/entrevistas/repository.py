import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.features.notificaciones.emisor import emitir_notificacion
from app.models.candidato import CandidateProfile
from app.models.empresa import CompanyMember
from app.models.entrevista import Interview
from app.models.notificacion import Notification
from app.models.postulacion import (
    Application,
    ApplicationStageHistory,
    ApplicationStatusHistory,
)
from app.models.vacante import JobPosting, JobSelectionStage


class EntrevistasRepository:
    def __init__(self, db: Session):
        self.db = db

    def obtener_entrevista(self, interview_id: uuid.UUID) -> Optional[Interview]:
        stmt = (
            select(Interview)
            .options(
                joinedload(Interview.application)
                .joinedload(Application.job_posting)
                .joinedload(JobPosting.company),
                joinedload(Interview.application)
                .joinedload(Application.candidate)
                .joinedload(CandidateProfile.user),
            )
            .where(Interview.id == interview_id)
        )
        return self.db.scalar(stmt)

    def obtener_postulacion(self, application_id: uuid.UUID) -> Optional[Application]:
        stmt = (
            select(Application)
            .options(
                joinedload(Application.job_posting).joinedload(JobPosting.company),
                joinedload(Application.candidate).joinedload(CandidateProfile.user),
                joinedload(Application.current_stage),
            )
            .where(Application.id == application_id)
        )
        return self.db.scalar(stmt)

    def listar_por_postulacion(self, application_id: uuid.UUID) -> list[Interview]:
        stmt = (
            select(Interview)
            .options(
                joinedload(Interview.application)
                .joinedload(Application.job_posting)
                .joinedload(JobPosting.company),
                joinedload(Interview.application)
                .joinedload(Application.candidate),
            )
            .where(Interview.application_id == application_id)
            .order_by(Interview.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def listar_por_empresa_y_rango(
        self, company_id: uuid.UUID, desde: datetime, hasta: datetime
    ) -> list[Interview]:
        """Entrevistas de las vacantes de la empresa que empiezan en [desde, hasta)."""
        stmt = (
            select(Interview)
            .join(Application, Interview.application_id == Application.id)
            .join(JobPosting, Application.job_id == JobPosting.id)
            .options(
                contains_eager(Interview.application)
                .contains_eager(Application.job_posting)
                .joinedload(JobPosting.company),
                contains_eager(Interview.application).joinedload(Application.candidate),
            )
            .where(
                JobPosting.company_id == company_id,
                Interview.scheduled_start >= desde,
                Interview.scheduled_start < hasta,
            )
            .order_by(Interview.scheduled_start.asc())
        )
        return list(self.db.scalars(stmt).all())

    def guardar_entrevista(self, entrevista: Interview) -> Interview:
        self.db.add(entrevista)
        self.db.flush()
        return entrevista

    def obtener_miembro_empresa(self, user_id: uuid.UUID) -> Optional[CompanyMember]:
        stmt = (
            select(CompanyMember)
            .options(joinedload(CompanyMember.company))
            .where(CompanyMember.user_id == user_id, CompanyMember.is_active.is_(True))
        )
        return self.db.scalar(stmt)

    def obtener_perfil_candidato(self, user_id: uuid.UUID) -> Optional[CandidateProfile]:
        stmt = (
            select(CandidateProfile)
            .options(joinedload(CandidateProfile.user))
            .where(CandidateProfile.user_id == user_id)
        )
        return self.db.scalar(stmt)

    def obtener_etapas_vacante(self, job_id: uuid.UUID) -> list[JobSelectionStage]:
        stmt = (
            select(JobSelectionStage)
            .where(JobSelectionStage.job_posting_id == job_id)
            .order_by(JobSelectionStage.stage_number.asc())
        )
        return list(self.db.scalars(stmt).all())

    def crear_notificacion(
        self,
        user_id: uuid.UUID,
        tipo: str,
        titulo: str,
        cuerpo: str,
        enlace: str | None = None,
    ) -> Notification | None:
        """Respeta las preferencias del destinatario y manda el push (HU-21)."""
        return emitir_notificacion(self.db, user_id, tipo, titulo, cuerpo, enlace)

    def mover_postulacion_a_etapa(
        self,
        application: Application,
        nueva_etapa: JobSelectionStage,
        nuevo_status: str,
        user_id: uuid.UUID | None = None,
        observacion: str | None = "Auto-sync tras confirmar entrevista",
    ) -> None:
        # Cerrar etapa anterior abierta
        stmt_open_stage = select(ApplicationStageHistory).where(
            ApplicationStageHistory.application_id == application.id,
            ApplicationStageHistory.left_at.is_(None),
        )
        stage_abierta = self.db.scalar(stmt_open_stage)
        if stage_abierta:
            stage_abierta.left_at = datetime.now(timezone.utc)
            stage_abierta.result = "passed"

        estado_anterior = application.current_status
        application.current_stage_id = nueva_etapa.id
        application.current_status = nuevo_status
        application.updated_at = datetime.now(timezone.utc)

        # Registrar nuevo ingreso de etapa
        nuevo_ingreso = ApplicationStageHistory(
            application_id=application.id,
            stage_id=nueva_etapa.id,
            entered_at=datetime.now(timezone.utc),
            changed_by=user_id,
            result="pending",
            notes=observacion,
        )
        self.db.add(nuevo_ingreso)

        # Registrar historial de estado
        hist_estado = ApplicationStatusHistory(
            application_id=application.id,
            from_status=estado_anterior,
            to_status=nuevo_status,
            changed_by=user_id,
            reason=f"Avance a etapa: {nueva_etapa.name}. {observacion or ''}".strip(),
        )
        self.db.add(hist_estado)
