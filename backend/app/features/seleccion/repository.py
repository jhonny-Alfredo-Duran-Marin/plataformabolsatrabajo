import uuid
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.candidato import CandidateEducation, CandidateProfile
from app.models.empresa import Company, CompanyMember
from app.models.notificacion import Notification
from app.models.postulacion import (
    Application,
    ApplicationNote,
    ApplicationStageHistory,
    ApplicationStatusHistory,
)
from app.models.usuario import AppUser
from app.models.vacante import JobPosting, JobSelectionStage


class SeleccionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_miembro_empresa(self, user_id: uuid.UUID) -> CompanyMember | None:
        stmt = (
            select(CompanyMember)
            .options(joinedload(CompanyMember.company))
            .where(CompanyMember.user_id == user_id, CompanyMember.is_active == True)
        )
        return self.db.scalar(stmt)

    def listar_vacantes_empresa(self, company_id: uuid.UUID) -> list[JobPosting]:
        stmt = (
            select(JobPosting)
            .options(selectinload(JobPosting.stages))
            .where(JobPosting.company_id == company_id)
            .order_by(JobPosting.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def obtener_vacante(self, job_id: uuid.UUID, company_id: uuid.UUID) -> JobPosting | None:
        stmt = (
            select(JobPosting)
            .options(selectinload(JobPosting.stages))
            .where(JobPosting.id == job_id, JobPosting.company_id == company_id)
        )
        return self.db.scalar(stmt)

    def obtener_etapas_vacante(self, job_id: uuid.UUID) -> list[JobSelectionStage]:
        stmt = (
            select(JobSelectionStage)
            .where(JobSelectionStage.job_posting_id == job_id)
            .order_by(JobSelectionStage.stage_number.asc())
        )
        return list(self.db.scalars(stmt).all())

    def configurar_etapas_vacante(
        self, job_id: uuid.UUID, nuevas_etapas: list[dict]
    ) -> list[JobSelectionStage]:
        etapas_actuales = self.obtener_etapas_vacante(job_id)
        mapa_actuales = {e.id: e for e in etapas_actuales}

        resultado: list[JobSelectionStage] = []
        ids_a_conservar: set[uuid.UUID] = set()

        for idx, item in enumerate(nuevas_etapas, start=1):
            stage_id = item.get("id")
            if stage_id and stage_id in mapa_actuales:
                # Actualizar etapa existente
                etapa = mapa_actuales[stage_id]
                etapa.stage_number = idx
                etapa.name = item["name"].strip()
                etapa.description = item.get("description")
                etapa.is_terminal = item.get("is_terminal", False)
                etapa.updated_at = datetime.now()
                ids_a_conservar.add(stage_id)
                resultado.append(etapa)
            else:
                # Crear nueva etapa
                nueva = JobSelectionStage(
                    job_posting_id=job_id,
                    stage_number=idx,
                    name=item["name"].strip(),
                    description=item.get("description"),
                    is_terminal=item.get("is_terminal", False),
                )
                self.db.add(nueva)
                resultado.append(nueva)

        # Eliminar etapas que ya no están en la lista (si no tienen referencias que lo impidan)
        for e in etapas_actuales:
            if e.id not in ids_a_conservar:
                self.db.delete(e)

        self.db.flush()
        return resultado

    def obtener_postulaciones_vacante(self, job_id: uuid.UUID) -> list[Application]:
        stmt = (
            select(Application)
            .options(
                joinedload(Application.candidate).joinedload(CandidateProfile.user),
                joinedload(Application.candidate).selectinload(CandidateProfile.educations).joinedload(CandidateEducation.field_of_study),
                joinedload(Application.current_stage),
                selectinload(Application.notes),
            )
            .where(Application.job_id == job_id)
            .order_by(Application.applied_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def obtener_postulacion_por_id(self, application_id: uuid.UUID) -> Application | None:
        stmt = (
            select(Application)
            .options(
                joinedload(Application.job_posting).joinedload(JobPosting.company),
                joinedload(Application.candidate).joinedload(CandidateProfile.user),
                joinedload(Application.current_stage),
                selectinload(Application.status_history),
                selectinload(Application.stage_history),
                selectinload(Application.notes).joinedload(ApplicationNote.member).joinedload(CompanyMember.user),
            )
            .where(Application.id == application_id)
        )
        return self.db.scalar(stmt)

    def avanzar_etapa_postulacion(
        self,
        application: Application,
        nueva_etapa: JobSelectionStage,
        nuevo_status: str,
        user_id: uuid.UUID,
        observacion: str | None = None,
    ) -> None:
        # Cerrar etapa anterior abierta
        stmt_open_stage = select(ApplicationStageHistory).where(
            ApplicationStageHistory.application_id == application.id,
            ApplicationStageHistory.left_at.is_(None),
        )
        stage_abierta = self.db.scalar(stmt_open_stage)
        if stage_abierta:
            stage_abierta.left_at = datetime.now()
            stage_abierta.result = "passed"
            if observacion:
                stage_abierta.notes = observacion

        estado_anterior = application.current_status
        application.current_stage_id = nueva_etapa.id
        application.current_status = nuevo_status
        application.updated_at = datetime.now()

        # Registrar nuevo ingreso de etapa
        nuevo_ingreso = ApplicationStageHistory(
            application_id=application.id,
            stage_id=nueva_etapa.id,
            entered_at=datetime.now(),
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

    def descartar_candidato_postulacion(
        self,
        application: Application,
        user_id: uuid.UUID,
        motivo: str | None = None,
    ) -> None:
        # Cerrar etapa anterior abierta como failed
        stmt_open_stage = select(ApplicationStageHistory).where(
            ApplicationStageHistory.application_id == application.id,
            ApplicationStageHistory.left_at.is_(None),
        )
        stage_abierta = self.db.scalar(stmt_open_stage)
        if stage_abierta:
            stage_abierta.left_at = datetime.now()
            stage_abierta.result = "failed"
            stage_abierta.notes = motivo

        estado_anterior = application.current_status
        application.current_status = "rejected"
        application.updated_at = datetime.now()

        # Registrar historial de estado
        hist_estado = ApplicationStatusHistory(
            application_id=application.id,
            from_status=estado_anterior,
            to_status="rejected",
            changed_by=user_id,
            reason=motivo or "Candidato no seleccionado para la vacante",
        )
        self.db.add(hist_estado)

    def crear_notificacion(
        self,
        user_id: uuid.UUID,
        tipo: str,
        titulo: str,
        cuerpo: str,
        enlace: str | None = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            notification_type=tipo,
            title=titulo,
            body=cuerpo,
            link=enlace,
        )
        self.db.add(notif)
        return notif

    def crear_nota_interna(
        self,
        application_id: uuid.UUID,
        company_member_id: uuid.UUID,
        contenido: str,
    ) -> ApplicationNote:
        nota = ApplicationNote(
            application_id=application_id,
            company_member_id=company_member_id,
            content=contenido.strip(),
        )
        self.db.add(nota)
        return nota

    def listar_notas_internas(self, application_id: uuid.UUID) -> list[ApplicationNote]:
        stmt = (
            select(ApplicationNote)
            .options(
                joinedload(ApplicationNote.member).joinedload(CompanyMember.user)
            )
            .where(ApplicationNote.application_id == application_id)
            .order_by(ApplicationNote.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())
