import uuid
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.features.seleccion.schema import EtapaItemDTO
from app.models.candidato import CandidateProfile
from app.models.oferta import JobPosting
from app.models.seleccion import (
    Application,
    ApplicationNote,
    ApplicationStageHistory,
    JobSelectionStage,
    Notification,
)
from app.models.usuario import AppUser


class SeleccionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_etapas_vacante(self, vacante_id: uuid.UUID) -> list[JobSelectionStage]:
        """Obtiene las etapas configuradas para una vacante ordenadas por secuencia."""
        stmt = (
            select(JobSelectionStage)
            .where(JobSelectionStage.job_posting_id == vacante_id)
            .order_by(JobSelectionStage.stage_number.asc())
        )
        return list(self.db.scalars(stmt))

    def inicializar_etapas_por_defecto(self, vacante_id: uuid.UUID) -> list[JobSelectionStage]:
        """Crea las etapas por defecto para una vacante si no tiene ninguna."""
        etapas_defecto = [
            JobSelectionStage(
                job_posting_id=vacante_id,
                stage_number=1,
                name="Postulado / Preselección",
                description="Revisión inicial del currículum y perfil.",
                is_terminal=False,
            ),
            JobSelectionStage(
                job_posting_id=vacante_id,
                stage_number=2,
                name="Entrevista Inicial",
                description="Primer contacto y entrevista con el equipo.",
                is_terminal=False,
            ),
            JobSelectionStage(
                job_posting_id=vacante_id,
                stage_number=3,
                name="Evaluación Técnica",
                description="Pruebas de competencias del puesto.",
                is_terminal=False,
            ),
            JobSelectionStage(
                job_posting_id=vacante_id,
                stage_number=4,
                name="Oferta y Contratación",
                description="Fase final de contratación.",
                is_terminal=True,
            ),
        ]
        self.db.add_all(etapas_defecto)
        self.db.commit()
        return self.obtener_etapas_vacante(vacante_id)

    def configurar_etapas_vacante(
        self, vacante_id: uuid.UUID, etapas_dto: list[EtapaItemDTO]
    ) -> list[JobSelectionStage]:
        """Reemplaza o actualiza las etapas del proceso de selección de una vacante."""
        etapas_existentes = {e.id: e for e in self.obtener_etapas_vacante(vacante_id)}
        ids_en_request = {e.id for e in etapas_dto if e.id is not None}

        # Actualizar o insertar
        for dto in etapas_dto:
            if dto.id and dto.id in etapas_existentes:
                etapa = etapas_existentes[dto.id]
                etapa.stage_number = dto.stage_number
                etapa.name = dto.name
                etapa.description = dto.description
                etapa.is_terminal = dto.is_terminal
            else:
                nueva_etapa = JobSelectionStage(
                    job_posting_id=vacante_id,
                    stage_number=dto.stage_number,
                    name=dto.name,
                    description=dto.description,
                    is_terminal=dto.is_terminal,
                )
                self.db.add(nueva_etapa)

        # Eliminar etapas que ya no están si no tienen postulaciones activas
        for etapa_id, etapa in etapas_existentes.items():
            if etapa_id not in ids_en_request:
                self.db.delete(etapa)

        self.db.commit()
        return self.obtener_etapas_vacante(vacante_id)

    def obtener_postulaciones_vacante(self, vacante_id: uuid.UUID) -> list[Application]:
        """Obtiene todas las postulaciones de una vacante con relaciones cargadas."""
        stmt = (
            select(Application)
            .where(Application.job_id == vacante_id)
            .options(
                joinedload(Application.candidate),
                joinedload(Application.current_stage),
                selectinload(Application.notes),
                selectinload(Application.stage_history),
            )
            .order_by(Application.applied_at.desc())
        )
        return list(self.db.scalars(stmt).unique())

    def obtener_postulacion_por_id(self, application_id: uuid.UUID) -> Application | None:
        """Obtiene una postulación por su ID con todas sus relaciones."""
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                joinedload(Application.candidate),
                joinedload(Application.job_posting).joinedload(JobPosting.company),
                joinedload(Application.current_stage),
                selectinload(Application.stage_history).joinedload(ApplicationStageHistory.stage),
                selectinload(Application.stage_history).joinedload(ApplicationStageHistory.changed_by_user),
                selectinload(Application.notes).joinedload(ApplicationNote.author),
            )
        )
        return self.db.scalar(stmt)

    def mover_candidato_etapa(
        self,
        application: Application,
        nueva_etapa: JobSelectionStage,
        usuario_id: uuid.UUID | None,
        observacion: str | None,
    ) -> Application:
        """Avanza al candidato a una nueva etapa, registra la auditoría y dispara una notificación."""
        stmt_hist = (
            select(ApplicationStageHistory)
            .where(
                ApplicationStageHistory.application_id == application.id,
                ApplicationStageHistory.left_at.is_(None),
            )
            .order_by(ApplicationStageHistory.entered_at.desc())
        )
        hist_activo = self.db.scalar(stmt_hist)
        if hist_activo:
            hist_activo.left_at = func.now()
            hist_activo.result = "passed"

        application.current_stage_id = nueva_etapa.id
        application.current_status = "hired" if nueva_etapa.is_terminal else "in_review"

        nuevo_hist = ApplicationStageHistory(
            application_id=application.id,
            stage_id=nueva_etapa.id,
            entered_at=func.now(),
            changed_by=usuario_id,
            result="pending",
            notes=observacion,
        )
        self.db.add(nuevo_hist)

        # Notificación al candidato
        cand_user_id = application.candidate.user_id if application.candidate else None
        if cand_user_id:
            empresa_nombre = (
                application.job_posting.company.trade_name
                or application.job_posting.company.legal_name
                if application.job_posting and application.job_posting.company
                else "la empresa"
            )
            notif = Notification(
                user_id=cand_user_id,
                notification_type="stage_change",
                title=f"Avance en tu postulación: {application.job_posting.title if application.job_posting else 'Oferta'}",
                body=f"¡Felicidades! Has avanzado a la etapa '{nueva_etapa.name}' en el proceso de selección de {empresa_nombre}.",
                link=f"/vacantes/{application.job_id}",
            )
            self.db.add(notif)

        self.db.commit()
        self.db.refresh(application)
        return application

    def descartar_candidato(
        self,
        application: Application,
        usuario_id: uuid.UUID | None,
        motivo: str | None,
    ) -> Application:
        """Marca al candidato como descartado, registra auditoría y bloquea futuros avances."""
        stmt_hist = (
            select(ApplicationStageHistory)
            .where(
                ApplicationStageHistory.application_id == application.id,
                ApplicationStageHistory.left_at.is_(None),
            )
            .order_by(ApplicationStageHistory.entered_at.desc())
        )
        hist_activo = self.db.scalar(stmt_hist)
        if hist_activo:
            hist_activo.left_at = func.now()
            hist_activo.result = "rejected"
            if motivo:
                hist_activo.notes = f"Descarte: {motivo}"

        application.current_status = "rejected"

        cand_user_id = application.candidate.user_id if application.candidate else None
        if cand_user_id:
            empresa_nombre = (
                application.job_posting.company.trade_name
                or application.job_posting.company.legal_name
                if application.job_posting and application.job_posting.company
                else "la empresa"
            )
            notif = Notification(
                user_id=cand_user_id,
                notification_type="stage_change",
                title=f"Estado de tu postulación: {application.job_posting.title if application.job_posting else 'Oferta'}",
                body=f"Tu postulación para '{application.job_posting.title if application.job_posting else ''}' en {empresa_nombre} no ha avanzado en esta ocasión. {('Motivo: ' + motivo) if motivo else ''}",
                link=f"/vacantes/{application.job_id}",
            )
            self.db.add(notif)

        self.db.commit()
        self.db.refresh(application)
        return application

    def agregar_nota_interna(
        self,
        application_id: uuid.UUID,
        usuario_id: uuid.UUID,
        contenido: str,
    ) -> ApplicationNote:
        """Registra una nota interna privada del equipo de selección."""
        nota = ApplicationNote(
            application_id=application_id,
            company_member_id=usuario_id,
            content=contenido.strip(),
        )
        self.db.add(nota)
        self.db.commit()
        self.db.refresh(nota)
        return nota

    def obtener_notas_postulacion(self, application_id: uuid.UUID) -> list[ApplicationNote]:
        """Obtiene las notas internas asociadas a una postulación."""
        stmt = (
            select(ApplicationNote)
            .where(ApplicationNote.application_id == application_id)
            .options(joinedload(ApplicationNote.author))
            .order_by(ApplicationNote.created_at.desc())
        )
        return list(self.db.scalars(stmt))
