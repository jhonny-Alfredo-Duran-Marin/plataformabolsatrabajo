import uuid
from datetime import date, datetime
from sqlalchemy import func
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
    PostulacionItemResponse,
    ResumenPostulacionesResponse,
)
from app.models.postulacion import Application


class PostulacionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PostulacionRepository(db)
        self.bitacora = BitacoraService(db)

    def _obtener_candidato_o_error(self, user_id: uuid.UUID):
        candidato = self.repo.obtener_perfil_candidato(user_id)
        if not candidato:
            raise NotFoundException("Perfil de egresado/candidato no encontrado para este usuario.")
        return candidato

    def _mapear_postulacion_item(self, app: Application) -> PostulacionItemResponse:
        job = app.job_posting
        company = job.company if job else None

        info_estado = ESTADOS_INFO.get(
            app.current_status,
            {"label": app.current_status.capitalize(), "color": "gray"},
        )

        nombre_empresa = (
            company.trade_name or company.legal_name
            if company
            else "Empresa confidencial"
        )
        ciudad_empresa = (company.city if company else None) or (job.city if job else None)

        # Determinar si puede retirar la postulación
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

    def obtener_mis_postulaciones(
        self,
        user_id: uuid.UUID,
        estado: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        busqueda: str | None = None,
    ) -> ResumenPostulacionesResponse:
        candidato = self._obtener_candidato_o_error(user_id)

        # Consultar todas sin filtro para calcular métricas generales
        todas = self.repo.listar_postulaciones_candidato(candidato.id)

        # Consultar con filtros aplicados para la lista mostrada
        filtradas = self.repo.listar_postulaciones_candidato(
            candidato.id,
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            busqueda=busqueda,
        )

        total = len(todas)
        en_revision = sum(1 for a in todas if a.current_status in ("applied", "screening", "in_review"))
        entrevistas_ofertas = sum(1 for a in todas if a.current_status in ("shortlisted", "interview", "assessment", "offer"))
        contratados = sum(1 for a in todas if a.current_status == "hired")
        finalizadas = sum(1 for a in todas if a.current_status in ("hired", "rejected", "withdrawn"))
        activas = total - finalizadas

        items = [self._mapear_postulacion_item(a) for a in filtradas]

        return ResumenPostulacionesResponse(
            total=total,
            activas=activas,
            en_revision=en_revision,
            entrevistas_ofertas=entrevistas_ofertas,
            contratados=contratados,
            finalizadas=finalizadas,
            postulaciones=items,
        )

    def obtener_detalle_postulacion(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> DetallePostulacionResponse:
        candidato = self._obtener_candidato_o_error(user_id)
        app = self.repo.obtener_por_id_y_candidato(application_id, candidato.id)

        if not app:
            raise NotFoundException("La postulación solicitada no existe o no pertenece al candidato.")

        job = app.job_posting
        company = job.company if job else None

        # Habilidades de la vacante
        habilidades_list: list[HabilidadItem] = []
        if job and job.skills:
            for js in job.skills:
                if js.skill:
                    habilidades_list.append(
                        HabilidadItem(
                            nombre=js.skill.name,
                            importancia=js.importance,
                            nivel_minimo=js.min_proficiency,
                        )
                    )

        # Detalle de la vacante
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
            fecha_publicacion=job.published_at,
            fecha_limite=job.application_deadline,
        )

        # Historial de cambios de estado ordenados por fecha ascendente
        historial_estados_sorted = sorted(app.status_history, key=lambda h: h.created_at)
        historial_estados_resp: list[HistorialEstadoResponse] = []
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

        # Si no hay historial explícito pero hay estado, crear al menos el registro inicial de postulación
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

        # Historial de etapas
        historial_etapas_resp: list[EtapaHistorialResponse] = []
        for stg in app.stage_history:
            historial_etapas_resp.append(
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
            )

        postulacion_item = self._mapear_postulacion_item(app)

        return DetallePostulacionResponse(
            postulacion=postulacion_item,
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

        self.repo.registrar_cambio_estado(
            application=app,
            nuevo_estado="withdrawn",
            user_id=user_id,
            motivo=motivo_final,
        )

        self.bitacora.registrar(
            modulo="postulaciones",
            accion="retirar_postulacion",
            usuario_id=user_id,
            ip=ip,
            detalles=f"postulacion_id={app.id} estado_anterior={estado_anterior} motivo={motivo_final}",
        )

        self.db.commit()
        return self._mapear_postulacion_item(app)
