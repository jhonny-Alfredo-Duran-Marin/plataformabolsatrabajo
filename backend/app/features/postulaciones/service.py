import uuid
from datetime import date, datetime
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.common.exceptions import BadRequestException, NotFoundException
from app.features.bitacora.service import BitacoraService
from app.features.postulaciones.repository import PostulacionRepository
from app.features.postulaciones.schema import (
    ESTADOS_INFO,
    MODALIDADES_INFO,
    TIPOS_EMPLEO_INFO,
    DetallePostulacionResponse,
    DetalleVacanteResponse,
    EtapaHistorialResponse,
    HabilidadItem,
    HistorialEstadoResponse,
    PostulacionCreate,
    PostulacionItemResponse,
    PostulacionListResponse,
    PostulacionResponse,
    ResumenPostulacionesResponse,
)
from app.models.candidato import CandidateProfile
from app.models.empresa import Company
from app.models.postulacion import Application, ApplicationAnswer, ApplicationStatusHistory
from app.models.vacante import JobPosting, ScreeningOption, ScreeningQuestion


class PostulacionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PostulacionRepository(db)
        self.bitacora = BitacoraService(db)

    # ─── Postularse a una vacante — HU-14 ───────────────────────────────────

    def postular_vacante(self, user_id: str, data: PostulacionCreate) -> PostulacionResponse:
        candidate = self.db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
        if not candidate:
            raise HTTPException(status_code=403, detail="Perfil de candidato no encontrado.")

        if candidate.verification_status != "verified":
            raise HTTPException(status_code=403, detail="Solo un egresado validado puede postularse.")

        vacante = self.db.query(JobPosting).filter(JobPosting.id == data.job_id).first()
        if not vacante:
            raise HTTPException(status_code=404, detail="La vacante no existe.")

        existing_app = (
            self.db.query(Application)
            .filter(
                Application.candidate_id == candidate.id,
                Application.job_id == data.job_id,
                Application.current_status != "withdrawn",
            )
            .first()
        )
        if existing_app:
            raise HTTPException(status_code=400, detail="Ya te has postulado a esta vacante.")

        required_questions = (
            self.db.query(ScreeningQuestion)
            .filter(ScreeningQuestion.job_posting_id == data.job_id, ScreeningQuestion.is_required == True)
            .all()
        )
        required_q_ids = {str(q.id) for q in required_questions}
        provided_q_ids = {str(ans.question_id) for ans in data.answers}
        missing_q_ids = required_q_ids - provided_q_ids
        if missing_q_ids:
            raise HTTPException(status_code=400, detail="Faltan respuestas a preguntas requeridas de la vacante.")

        new_app = Application(candidate_id=candidate.id, job_id=data.job_id, current_status="applied")
        self.db.add(new_app)
        self.db.flush()

        knockout_questions = {
            q.id: q
            for q in self.db.query(ScreeningQuestion).filter(
                ScreeningQuestion.job_posting_id == data.job_id, ScreeningQuestion.is_knockout == True
            )
        }
        motivo_descarte: str | None = None

        for ans in data.answers:
            self.db.add(
                ApplicationAnswer(
                    application_id=new_app.id,
                    question_id=ans.question_id,
                    selected_option_id=ans.selected_option_id,
                    answer_text=ans.answer_text,
                    answer_number=ans.answer_number,
                )
            )

            pregunta = knockout_questions.get(ans.question_id)
            if pregunta is not None and ans.selected_option_id is not None:
                opcion = self.db.query(ScreeningOption).filter(ScreeningOption.id == ans.selected_option_id).first()
                if opcion is not None and not opcion.is_accepted:
                    motivo_descarte = f"Respuesta excluyente en: {pregunta.question_text}"

        if motivo_descarte:
            new_app.current_status = "rejected"
            self.db.add(
                ApplicationStatusHistory(
                    application_id=new_app.id,
                    from_status="applied",
                    to_status="rejected",
                    reason=motivo_descarte,
                )
            )

        self.db.commit()
        self.db.refresh(new_app)

        mensaje = (
            f"Tu postulación fue descartada automáticamente: {motivo_descarte}"
            if motivo_descarte
            else "Postulación exitosa"
        )
        return PostulacionResponse(
            id=new_app.id,
            job_id=new_app.job_id,
            current_status=new_app.current_status,
            message=mensaje,
        )

    def obtener_mis_postulaciones(self, user_id: str) -> List[PostulacionListResponse]:
        """Listado simple usado por el panel del egresado (HU-14)."""
        candidate = self.db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
        if not candidate:
            return []

        results = (
            self.db.query(Application, JobPosting, Company)
            .join(JobPosting, Application.job_id == JobPosting.id)
            .join(Company, JobPosting.company_id == Company.id)
            .filter(Application.candidate_id == candidate.id)
            .order_by(Application.applied_at.desc())
            .all()
        )

        return [
            PostulacionListResponse(
                id=app.id,
                job_id=job.id,
                job_title=job.title,
                company_name=comp.legal_name,
                current_status=app.current_status,
                applied_at=app.applied_at,
            )
            for app, job, comp in results
        ]

    # ─── Seguimiento y retiro de postulaciones — HU-15 ──────────────────────

    def _obtener_candidato_o_error(self, user_id: uuid.UUID) -> CandidateProfile:
        candidato = self.repo.obtener_perfil_candidato(user_id)
        if not candidato:
            raise NotFoundException("Perfil de egresado/candidato no encontrado para este usuario.")
        return candidato

    def _mapear_postulacion_item(self, app: Application) -> PostulacionItemResponse:
        job = app.job_posting
        company = job.company if job else None

        info_estado = ESTADOS_INFO.get(app.current_status, {"label": app.current_status.capitalize(), "color": "gray"})
        nombre_empresa = (company.trade_name or company.legal_name) if company else "Empresa confidencial"
        ciudad_empresa = (company.city if company else None) or (job.city if job else None)
        puede_retirar = app.current_status not in ("hired", "rejected", "withdrawn")

        return PostulacionItemResponse(
            id=app.id,
            job_id=app.job_id,
            job_titulo=job.title if job else "Vacante",
            empresa_id=company.id if company else uuid.uuid4(),
            empresa_nombre=nombre_empresa,
            empresa_ciudad=ciudad_empresa,
            modalidad=job.work_modality if job else "onsite",
            modalidad_label=MODALIDADES_INFO.get(job.work_modality, job.work_modality.capitalize()) if job else "Presencial",
            tipo_empleo=job.employment_type if job else "permanent",
            tipo_empleo_label=TIPOS_EMPLEO_INFO.get(job.employment_type, job.employment_type.capitalize()) if job else "Tiempo Completo",
            salario_min=job.salary_min if job else None,
            salario_max=job.salary_max if job else None,
            currency=job.currency if job else "BOB",
            salario_visible=job.salary_visible if job else False,
            estado=app.current_status,
            estado_label=info_estado["label"],
            estado_color=info_estado["color"],
            etapa_actual_nombre=app.current_stage.name if app.current_stage else None,
            fecha_postulacion=app.applied_at,
            fecha_ultimo_cambio=app.updated_at or app.applied_at,
            cover_letter=app.cover_letter,
            puede_retirar=puede_retirar,
        )

    def obtener_resumen_postulaciones(
        self,
        user_id: uuid.UUID,
        estado: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        busqueda: str | None = None,
    ) -> ResumenPostulacionesResponse:
        candidato = self._obtener_candidato_o_error(user_id)

        todas = self.repo.listar_postulaciones_candidato(candidato.id)
        filtradas = self.repo.listar_postulaciones_candidato(
            candidato.id, estado=estado, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, busqueda=busqueda
        )

        total = len(todas)
        en_revision = sum(1 for a in todas if a.current_status in ("applied", "screening", "in_review"))
        entrevistas_ofertas = sum(1 for a in todas if a.current_status in ("shortlisted", "interview", "assessment", "offer"))
        contratados = sum(1 for a in todas if a.current_status == "hired")
        finalizadas = sum(1 for a in todas if a.current_status in ("hired", "rejected", "withdrawn"))
        activas = total - finalizadas

        return ResumenPostulacionesResponse(
            total=total,
            activas=activas,
            en_revision=en_revision,
            entrevistas_ofertas=entrevistas_ofertas,
            contratados=contratados,
            finalizadas=finalizadas,
            postulaciones=[self._mapear_postulacion_item(a) for a in filtradas],
        )

    def obtener_detalle_postulacion(self, user_id: uuid.UUID, application_id: uuid.UUID) -> DetallePostulacionResponse:
        candidato = self._obtener_candidato_o_error(user_id)
        app = self.repo.obtener_por_id_y_candidato(application_id, candidato.id)
        if not app:
            raise NotFoundException("La postulación solicitada no existe o no pertenece al candidato.")

        job = app.job_posting
        company = job.company if job else None

        habilidades_list = [
            HabilidadItem(nombre=js.skill.name, importancia=js.importance, nivel_minimo=js.min_proficiency)
            for js in (job.skills if job and job.skills else [])
            if js.skill
        ]

        vacante_resp = DetalleVacanteResponse(
            id=job.id if job else uuid.uuid4(),
            titulo=job.title if job else "Vacante no disponible",
            descripcion=job.description if job else "",
            empresa_id=company.id if company else uuid.uuid4(),
            empresa_nombre=(company.trade_name or company.legal_name) if company else "Confidencial",
            empresa_rubro=company.sector.name if (company and company.sector) else None,
            empresa_tamano=company.company_size if company else None,
            empresa_descripcion=company.description if company else None,
            ciudad=job.city if job else (company.city if company else None),
            pais=job.country_code if job else "BO",
            modalidad=job.work_modality if job else "onsite",
            modalidad_label=MODALIDADES_INFO.get(job.work_modality, "Presencial") if job else "Presencial",
            tipo_empleo=job.employment_type if job else "permanent",
            tipo_empleo_label=TIPOS_EMPLEO_INFO.get(job.employment_type, "Tiempo Completo") if job else "Tiempo Completo",
            seniority=job.seniority_level if job else None,
            anios_experiencia_min=job.min_years_experience if job else None,
            nivel_educativo_min=job.min_education_level if job else None,
            salario_min=job.salary_min if job else None,
            salario_max=job.salary_max if job else None,
            currency=job.currency if job else "BOB",
            salario_visible=job.salary_visible if job else False,
            posiciones_disponibles=job.positions_available if job else 1,
            habilidades=habilidades_list,
            fecha_publicacion=job.published_at if job else None,
            fecha_limite=job.application_deadline if job else None,
        )

        historial_estados_sorted = sorted(app.status_history, key=lambda h: h.created_at)
        historial_estados_resp = []
        for h in historial_estados_sorted:
            from_info = ESTADOS_INFO.get(h.from_status, {"label": h.from_status.capitalize()}) if h.from_status else None
            to_info = ESTADOS_INFO.get(h.to_status, {"label": h.to_status.capitalize(), "color": "blue"})
            historial_estados_resp.append(
                HistorialEstadoResponse(
                    id=h.id,
                    desde_estado=h.from_status,
                    desde_estado_label=from_info["label"] if from_info else None,
                    hacia_estado=h.to_status,
                    hacia_estado_label=to_info["label"],
                    hacia_estado_color=to_info["color"],
                    motivo=h.reason,
                    fecha=h.created_at,
                )
            )

        if not historial_estados_resp:
            info_actual = ESTADOS_INFO.get(app.current_status, {"label": app.current_status.capitalize(), "color": "blue"})
            historial_estados_resp.append(
                HistorialEstadoResponse(
                    id=uuid.uuid4(),
                    desde_estado=None,
                    desde_estado_label=None,
                    hacia_estado=app.current_status,
                    hacia_estado_label=info_actual["label"],
                    hacia_estado_color=info_actual["color"],
                    motivo="Postulación registrada en el sistema",
                    fecha=app.applied_at,
                )
            )

        historial_etapas_resp = [
            EtapaHistorialResponse(
                id=stg.id,
                etapa_nombre=stg.stage.name if stg.stage else "Etapa de selección",
                etapa_numero=stg.stage.stage_number if stg.stage else None,
                resultado=stg.result,
                resultado_label="Aprobada" if stg.result == "passed" else ("No superada" if stg.result == "failed" else "En proceso"),
                notas=stg.notes,
                fecha_ingreso=stg.entered_at,
                fecha_salida=stg.left_at,
            )
            for stg in app.stage_history
        ]

        return DetallePostulacionResponse(
            postulacion=self._mapear_postulacion_item(app),
            vacante=vacante_resp,
            historial_estados=historial_estados_resp,
            historial_etapas=historial_etapas_resp,
        )

    def retirar_postulacion(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        motivo: str | None = None,
        ip: str = "127.0.0.1",
    ) -> PostulacionItemResponse:
        candidato = self._obtener_candidato_o_error(user_id)
        app = self.repo.obtener_por_id_y_candidato(application_id, candidato.id)
        if not app:
            raise NotFoundException("La postulación no existe o no pertenece al candidato.")

        if app.current_status == "withdrawn":
            raise BadRequestException("La postulación ya se encuentra retirada.")
        if app.current_status in ("hired", "rejected"):
            raise BadRequestException(f"No es posible retirar una postulación en estado final ({app.current_status}).")

        estado_anterior = app.current_status
        app.current_status = "withdrawn"
        app.withdrawn_at = datetime.now()
        app.updated_at = datetime.now()

        motivo_final = motivo.strip() if motivo and motivo.strip() else "Retiro voluntario por el egresado"
        self.repo.registrar_cambio_estado(application=app, nuevo_estado="withdrawn", user_id=user_id, motivo=motivo_final)

        self.bitacora.registrar(
            modulo="postulaciones",
            accion="retirar_postulacion",
            usuario_id=user_id,
            ip=ip,
            detalles=f"postulacion_id={app.id} estado_anterior={estado_anterior} motivo={motivo_final}",
        )
        self.db.commit()

        return self._mapear_postulacion_item(app)
