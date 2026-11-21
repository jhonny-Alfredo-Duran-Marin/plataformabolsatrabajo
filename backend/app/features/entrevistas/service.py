import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.common.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.features.bitacora.service import BitacoraService
from app.features.entrevistas.repository import EntrevistasRepository
from app.features.notificaciones.estado_postulacion import notificar_cambio_estado
from app.features.entrevistas.schema import (
    EntrevistaCrear,
    EntrevistaOut,
    EntrevistaRechazar,
    EntrevistaReprogramar,
    EntrevistaRevisar,
)
from app.models.entrevista import Interview

# La agenda móvil pide un día o una semana; el tope evita consultas enormes.
_MAXIMO_AGENDA = timedelta(days=31)


class EntrevistasService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EntrevistasRepository(db)
        self.bitacora = BitacoraService(db)

    def _obtener_miembro_empresa(self, user_id: uuid.UUID):
        miembro = self.repo.obtener_miembro_empresa(user_id)
        if not miembro or not miembro.company:
            raise ForbiddenException("El usuario no pertenece a una empresa registrada o activa.")
        return miembro

    def _obtener_perfil_candidato(self, user_id: uuid.UUID):
        perfil = self.repo.obtener_perfil_candidato(user_id)
        if not perfil:
            raise ForbiddenException("El usuario no tiene un perfil de candidato registrado.")
        return perfil

    def _mapear_out(self, interview: Interview) -> EntrevistaOut:
        vacante_titulo = None
        candidato_nombre = None
        empresa_nombre = None

        if interview.application:
            if interview.application.job_posting:
                vacante_titulo = interview.application.job_posting.title
                if interview.application.job_posting.company:
                    empresa_nombre = (
                        interview.application.job_posting.company.trade_name
                        or interview.application.job_posting.company.legal_name
                    )
            if interview.application.candidate:
                candidato_nombre = (
                    f"{interview.application.candidate.first_name} {interview.application.candidate.last_name}"
                )

        return EntrevistaOut(
            id=interview.id,
            application_id=interview.application_id,
            scheduled_start=interview.scheduled_start,
            scheduled_end=interview.scheduled_end,
            modality=interview.modality,
            location=interview.location,
            meeting_url=interview.meeting_url,
            notes=interview.notes,
            status=interview.status,
            candidate_feedback=interview.candidate_feedback,
            rejection_count=interview.rejection_count,
            requires_manual_review=interview.requires_manual_review,
            created_by=interview.created_by,
            created_at=interview.created_at,
            updated_at=interview.updated_at,
            vacante_titulo=vacante_titulo,
            candidato_nombre=candidato_nombre,
            empresa_nombre=empresa_nombre,
        )

    # ─── LADO EMPRESA ────────────────────────────────────────────────────────

    def proponer_entrevista(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: EntrevistaCrear,
        ip: str = "127.0.0.1",
    ) -> EntrevistaOut:
        miembro = self._obtener_miembro_empresa(user_id)
        app = self.repo.obtener_postulacion(application_id)

        if not app or not app.job_posting or app.job_posting.company_id != miembro.company_id:
            raise NotFoundException("Postulación no encontrada o no pertenece a su empresa.")

        if app.current_status in ("rejected", "withdrawn"):
            raise BadRequestException(
                "No se pueden agendar entrevistas para postulaciones descartadas o retiradas."
            )

        entrevista = Interview(
            application_id=app.id,
            scheduled_start=data.scheduled_start,
            scheduled_end=data.scheduled_end,
            modality=data.modality,
            location=data.location.strip() if data.location else None,
            meeting_url=data.meeting_url.strip() if data.meeting_url else None,
            notes=data.notes.strip() if data.notes else None,
            status="pending_confirmation",
            rejection_count=0,
            requires_manual_review=False,
            created_by=user_id,
        )
        self.repo.guardar_entrevista(entrevista)

        # CP01: Notificar al candidato
        if app.candidate and app.candidate.user:
            empresa_nombre = miembro.company.trade_name or miembro.company.legal_name
            fecha_str = data.scheduled_start.strftime("%d/%m/%Y %H:%M")
            modalidad_str = "Presencial" if data.modality == "onsite" else "Virtual"
            self.repo.crear_notificacion(
                user_id=app.candidate.user.id,
                tipo="interview_proposal",
                titulo=f"Propuesta de entrevista: {app.job_posting.title}",
                cuerpo=f"{empresa_nombre} te ha propuesto una entrevista para el {fecha_str} ({modalidad_str}). Confirma o rechaza la propuesta.",
                enlace="/postulaciones",
            )

        self.bitacora.registrar(
            modulo="seleccion",
            accion="proponer_entrevista",
            usuario_id=user_id,
            ip=ip,
            detalles=f"postulacion_id={app.id} interview_id={entrevista.id} fecha={data.scheduled_start} modalidad={data.modality}",
        )
        self.db.commit()

        # Recargar con relaciones
        return self._mapear_out(self.repo.obtener_entrevista(entrevista.id))

    def listar_entrevistas_empresa(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> list[EntrevistaOut]:
        miembro = self._obtener_miembro_empresa(user_id)
        app = self.repo.obtener_postulacion(application_id)
        if not app or not app.job_posting or app.job_posting.company_id != miembro.company_id:
            raise NotFoundException("Postulación no encontrada o no pertenece a su empresa.")

        items = self.repo.listar_por_postulacion(application_id)
        return [self._mapear_out(it) for it in items]

    def listar_agenda_empresa(
        self,
        user_id: uuid.UUID,
        desde: datetime,
        hasta: datetime,
    ) -> list[EntrevistaOut]:
        """App móvil de empresas: entrevistas de todas sus vacantes que empiezan en [desde, hasta)."""
        # Sin zona horaria se asume UTC, igual que el resto del backend.
        desde = desde if desde.tzinfo else desde.replace(tzinfo=timezone.utc)
        hasta = hasta if hasta.tzinfo else hasta.replace(tzinfo=timezone.utc)
        if hasta <= desde:
            raise BadRequestException("La fecha final debe ser posterior a la inicial.")
        if hasta - desde > _MAXIMO_AGENDA:
            raise BadRequestException("Consultá la agenda de a 31 días como máximo.")

        miembro = self._obtener_miembro_empresa(user_id)
        items = self.repo.listar_por_empresa_y_rango(miembro.company_id, desde, hasta)
        return [self._mapear_out(it) for it in items]

    def reprogramar_entrevista(
        self,
        user_id: uuid.UUID,
        interview_id: uuid.UUID,
        data: EntrevistaReprogramar,
        ip: str = "127.0.0.1",
    ) -> EntrevistaOut:
        miembro = self._obtener_miembro_empresa(user_id)
        entrevista = self.repo.obtener_entrevista(interview_id)

        if (
            not entrevista
            or not entrevista.application
            or not entrevista.application.job_posting
            or entrevista.application.job_posting.company_id != miembro.company_id
        ):
            raise NotFoundException("Entrevista no encontrada o no pertenece a su empresa.")

        # Regla de 3 rechazos: 409 si requires_manual_review está activo
        if entrevista.requires_manual_review:
            raise ConflictException(
                "La entrevista acumula 3 rechazos y requiere revisión manual del reclutador antes de poder reprogramarse."
            )

        # Actualizar la MISMA fila conservando rejection_count
        entrevista.scheduled_start = data.scheduled_start
        entrevista.scheduled_end = data.scheduled_end
        entrevista.modality = data.modality
        entrevista.location = data.location.strip() if data.location else None
        entrevista.meeting_url = data.meeting_url.strip() if data.meeting_url else None
        entrevista.notes = data.notes.strip() if data.notes else None
        entrevista.status = "pending_confirmation"

        app = entrevista.application
        if app and app.candidate and app.candidate.user:
            empresa_nombre = miembro.company.trade_name or miembro.company.legal_name
            fecha_str = data.scheduled_start.strftime("%d/%m/%Y %H:%M")
            modalidad_str = "Presencial" if data.modality == "onsite" else "Virtual"
            self.repo.crear_notificacion(
                user_id=app.candidate.user.id,
                tipo="interview_rescheduled",
                titulo=f"Entrevista reprogramada: {app.job_posting.title}",
                cuerpo=f"{empresa_nombre} ha reprogramado tu entrevista para el {fecha_str} ({modalidad_str}). Confirma tu asistencia.",
                enlace="/postulaciones",
            )

        self.bitacora.registrar(
            modulo="seleccion",
            accion="reprogramar_entrevista",
            usuario_id=user_id,
            ip=ip,
            detalles=f"interview_id={entrevista.id} nueva_fecha={data.scheduled_start}",
        )
        self.db.commit()
        return self._mapear_out(entrevista)

    def cancelar_entrevista(
        self,
        user_id: uuid.UUID,
        interview_id: uuid.UUID,
        ip: str = "127.0.0.1",
    ) -> EntrevistaOut:
        miembro = self._obtener_miembro_empresa(user_id)
        entrevista = self.repo.obtener_entrevista(interview_id)

        if (
            not entrevista
            or not entrevista.application
            or not entrevista.application.job_posting
            or entrevista.application.job_posting.company_id != miembro.company_id
        ):
            raise NotFoundException("Entrevista no encontrada o no pertenece a su empresa.")

        entrevista.status = "cancelled"
        app = entrevista.application
        vacante_titulo = app.job_posting.title if app and app.job_posting else "la vacante"

        # CP04: Notificar a AMBAS partes
        # 1. Al candidato
        if app and app.candidate and app.candidate.user:
            self.repo.crear_notificacion(
                user_id=app.candidate.user.id,
                tipo="interview_cancelled",
                titulo=f"Entrevista cancelada: {vacante_titulo}",
                cuerpo=f"La entrevista prevista para el {entrevista.scheduled_start.strftime('%d/%m/%Y %H:%M')} ha sido cancelada por la empresa.",
                enlace="/postulaciones",
            )

        # 2. A la empresa (al reclutador)
        cand_nombre = (
            f"{app.candidate.first_name} {app.candidate.last_name}"
            if app and app.candidate
            else "el candidato"
        )
        self.repo.crear_notificacion(
            user_id=user_id,
            tipo="interview_cancelled",
            titulo=f"Entrevista cancelada: {vacante_titulo}",
            cuerpo=f"Has cancelado la entrevista con {cand_nombre}.",
            enlace="/seleccion",
        )

        self.bitacora.registrar(
            modulo="seleccion",
            accion="cancelar_entrevista",
            usuario_id=user_id,
            ip=ip,
            detalles=f"interview_id={entrevista.id}",
        )
        self.db.commit()
        return self._mapear_out(entrevista)

    def revisar_entrevista(
        self,
        user_id: uuid.UUID,
        interview_id: uuid.UUID,
        data: EntrevistaRevisar,
        ip: str = "127.0.0.1",
    ) -> EntrevistaOut:
        miembro = self._obtener_miembro_empresa(user_id)
        entrevista = self.repo.obtener_entrevista(interview_id)

        if (
            not entrevista
            or not entrevista.application
            or not entrevista.application.job_posting
            or entrevista.application.job_posting.company_id != miembro.company_id
        ):
            raise NotFoundException("Entrevista no encontrada o no pertenece a su empresa.")

        if data.aprobado:
            entrevista.requires_manual_review = False

        self.bitacora.registrar(
            modulo="seleccion",
            accion="revisar_entrevista",
            usuario_id=user_id,
            ip=ip,
            detalles=f"interview_id={entrevista.id} aprobado={data.aprobado}",
        )
        self.db.commit()
        return self._mapear_out(entrevista)

    # ─── LADO CANDIDATO ──────────────────────────────────────────────────────

    def listar_entrevistas_candidato(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
    ) -> list[EntrevistaOut]:
        perfil = self._obtener_perfil_candidato(user_id)
        app = self.repo.obtener_postulacion(application_id)

        if not app or app.candidate_id != perfil.id:
            raise NotFoundException("Postulación no encontrada.")

        items = self.repo.listar_por_postulacion(application_id)
        return [self._mapear_out(it) for it in items]

    def confirmar_entrevista_candidato(
        self,
        user_id: uuid.UUID,
        interview_id: uuid.UUID,
        ip: str = "127.0.0.1",
    ) -> EntrevistaOut:
        perfil = self._obtener_perfil_candidato(user_id)
        entrevista = self.repo.obtener_entrevista(interview_id)

        if not entrevista or not entrevista.application or entrevista.application.candidate_id != perfil.id:
            raise NotFoundException("Entrevista no encontrada.")

        if entrevista.status != "pending_confirmation":
            raise BadRequestException("Solo se pueden confirmar entrevistas pendientes de confirmación.")

        entrevista.status = "confirmed"
        app = entrevista.application
        estado_previo = app.current_status

        # Auto-sync Kanban: mover a etapa "entrevista" si no está en ella (Decisión 5)
        etapas = self.repo.obtener_etapas_vacante(app.job_id)
        etapa_actual_nombre = app.current_stage.name.lower() if app.current_stage else ""

        if "entrevista" not in etapa_actual_nombre:
            etapa_entrevista = next((e for e in etapas if "entrevista" in e.name.lower()), None)
            if etapa_entrevista:
                self.repo.mover_postulacion_a_etapa(
                    application=app,
                    nueva_etapa=etapa_entrevista,
                    nuevo_status="interview",
                    user_id=user_id,
                    observacion="Auto-sync: candidato confirmó la propuesta de entrevista",
                )
            elif app.current_status != "interview":
                app.current_status = "interview"

        # HU-36: si el sistema movió la postulación a «En entrevista», se avisa al egresado.
        if app.current_status != estado_previo:
            notificar_cambio_estado(self.db, app)

        # CP02: Notificar a la empresa
        cand_nombre = f"{perfil.first_name} {perfil.last_name}"
        vacante_titulo = app.job_posting.title if app.job_posting else "la vacante"
        fecha_str = entrevista.scheduled_start.strftime("%d/%m/%Y %H:%M")

        # Notificar al reclutador que creó la propuesta
        if entrevista.created_by:
            self.repo.crear_notificacion(
                user_id=entrevista.created_by,
                tipo="interview_confirmed",
                titulo=f"Entrevista confirmada: {vacante_titulo}",
                cuerpo=f"{cand_nombre} ha confirmado la entrevista para el {fecha_str}.",
                enlace="/seleccion",
            )

        self.bitacora.registrar(
            modulo="postulaciones",
            accion="confirmar_entrevista",
            usuario_id=user_id,
            ip=ip,
            detalles=f"interview_id={entrevista.id}",
        )
        self.db.commit()
        return self._mapear_out(entrevista)

    def rechazar_entrevista_candidato(
        self,
        user_id: uuid.UUID,
        interview_id: uuid.UUID,
        data: EntrevistaRechazar,
        ip: str = "127.0.0.1",
    ) -> EntrevistaOut:
        perfil = self._obtener_perfil_candidato(user_id)
        entrevista = self.repo.obtener_entrevista(interview_id)

        if not entrevista or not entrevista.application or entrevista.application.candidate_id != perfil.id:
            raise NotFoundException("Entrevista no encontrada.")

        if entrevista.status != "pending_confirmation":
            raise BadRequestException("Solo se pueden rechazar entrevistas pendientes de confirmación.")

        entrevista.status = "rejected"
        entrevista.candidate_feedback = data.motivo.strip()
        entrevista.rejection_count += 1

        # Regla de 3 rechazos: al llegar a 3 se bloquea para revisión manual
        if entrevista.rejection_count >= 3:
            entrevista.requires_manual_review = True

        app = entrevista.application
        cand_nombre = f"{perfil.first_name} {perfil.last_name}"
        vacante_titulo = app.job_posting.title if app and app.job_posting else "la vacante"

        # CP03: Notificar a la empresa
        if entrevista.created_by:
            if entrevista.requires_manual_review:
                cuerpo = (
                    f"{cand_nombre} ha rechazado la propuesta ({entrevista.rejection_count} rechazos acumulados). "
                    f"Motivo: '{data.motivo}'. La reprogramación queda bloqueada hasta revisión manual del reclutador."
                )
                titulo = f"Entrevista bloqueada (3 rechazos): {vacante_titulo}"
            else:
                cuerpo = (
                    f"{cand_nombre} ha rechazado la propuesta de entrevista ({entrevista.rejection_count} rechazos). "
                    f"Motivo: '{data.motivo}'. Puedes reprogramar una nueva fecha."
                )
                titulo = f"Entrevista rechazada: {vacante_titulo}"

            self.repo.crear_notificacion(
                user_id=entrevista.created_by,
                tipo="interview_rejected",
                titulo=titulo,
                cuerpo=cuerpo,
                enlace="/seleccion",
            )

        self.bitacora.registrar(
            modulo="postulaciones",
            accion="rechazar_entrevista",
            usuario_id=user_id,
            ip=ip,
            detalles=f"interview_id={entrevista.id} motivo={data.motivo} rejections={entrevista.rejection_count}",
        )
        self.db.commit()
        return self._mapear_out(entrevista)
