import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.common.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.features.bitacora.service import BitacoraService
from app.features.postulaciones.schema import ESTADOS_INFO, MODALIDADES_INFO, TIPOS_EMPLEO_INFO
from app.features.seleccion.repository import SeleccionRepository
from app.features.seleccion.schema import (
    AvanzarEtapaRequest,
    CandidatoPipelineItem,
    ConfigurarEtapasRequest,
    DescartarCandidatoRequest,
    EtapaResponse,
    NotaInternaRequest,
    NotaInternaResponse,
    PipelineVacanteResponse,
    VacanteResumenSeleccion,
)
from app.models.candidato import CandidateProfile
from app.models.empresa import CompanyMember
from app.models.postulacion import Application
from app.models.vacante import JobPosting, JobSelectionStage


class SeleccionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SeleccionRepository(db)
        self.bitacora = BitacoraService(db)

    def _obtener_miembro(self, user_id: uuid.UUID) -> CompanyMember:
        miembro = self.repo.obtener_miembro_empresa(user_id)
        if not miembro or not miembro.company:
            raise ForbiddenException("El usuario no pertenece a una empresa registrada o activa.")
        return miembro

    def _inferir_status_por_etapa(self, etapa: JobSelectionStage) -> str:
        nombre_lower = etapa.name.lower()
        if etapa.is_terminal or "contrat" in nombre_lower or "oferta" in nombre_lower:
            if "contrat" in nombre_lower:
                return "hired"
            return "offer"
        if "entrevista" in nombre_lower:
            return "interview"
        if "prueba" in nombre_lower or "evalua" in nombre_lower or "test" in nombre_lower:
            return "assessment"
        if "preselec" in nombre_lower or "shortlist" in nombre_lower:
            return "shortlisted"
        if "revis" in nombre_lower or "screening" in nombre_lower:
            return "screening"
        return "in_review"

    def listar_vacantes(self, user_id: uuid.UUID) -> list[VacanteResumenSeleccion]:
        miembro = self._obtener_miembro(user_id)
        vacantes = self.repo.listar_vacantes_empresa(miembro.company_id)

        resultado: list[VacanteResumenSeleccion] = []
        for vac in vacantes:
            apps = self.repo.obtener_postulaciones_vacante(vac.id)
            total = len(apps)
            descartados = sum(1 for a in apps if a.current_status in ("rejected", "withdrawn"))
            contratados = sum(1 for a in apps if a.current_status == "hired")
            activos = total - descartados - contratados

            resultado.append(
                VacanteResumenSeleccion(
                    id=vac.id,
                    titulo=vac.title,
                    seniority=vac.seniority_level,
                    modalidad=vac.work_modality,
                    modalidad_label=MODALIDADES_INFO.get(vac.work_modality, "Presencial"),
                    tipo_empleo=vac.employment_type,
                    tipo_empleo_label=TIPOS_EMPLEO_INFO.get(vac.employment_type, "Tiempo Completo"),
                    total_postulantes=total,
                    total_activos=activos,
                    total_descartados=descartados,
                    total_contratados=contratados,
                )
            )
        return resultado

    def obtener_etapas_vacante(self, user_id: uuid.UUID, job_id: uuid.UUID) -> list[EtapaResponse]:
        miembro = self._obtener_miembro(user_id)
        vacante = self.repo.obtener_vacante(job_id, miembro.company_id)
        if not vacante:
            raise NotFoundException("Vacante no encontrada o no pertenece a la empresa.")

        etapas = self.repo.obtener_etapas_vacante(job_id)
        postulaciones = self.repo.obtener_postulaciones_vacante(job_id)

        conteo_por_etapa: dict[uuid.UUID, int] = {}
        for app in postulaciones:
            if app.current_stage_id and app.current_status not in ("rejected", "withdrawn"):
                conteo_por_etapa[app.current_stage_id] = conteo_por_etapa.get(app.current_stage_id, 0) + 1

        return [
            EtapaResponse(
                id=e.id,
                job_posting_id=e.job_posting_id,
                stage_number=e.stage_number,
                name=e.name,
                description=e.description,
                is_terminal=e.is_terminal,
                total_candidatos=conteo_por_etapa.get(e.id, 0),
            )
            for e in etapas
        ]

    def configurar_etapas(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        data: ConfigurarEtapasRequest,
        ip: str = "127.0.0.1",
    ) -> list[EtapaResponse]:
        miembro = self._obtener_miembro(user_id)
        vacante = self.repo.obtener_vacante(job_id, miembro.company_id)
        if not vacante:
            raise NotFoundException("Vacante no encontrada o no pertenece a la empresa.")

        etapas_dict = [e.model_dump() for e in data.etapas]
        etapas_actualizadas = self.repo.configurar_etapas_vacante(job_id, etapas_dict)

        self.bitacora.registrar(
            modulo="seleccion",
            accion="configurar_etapas",
            usuario_id=user_id,
            ip=ip,
            detalles=f"vacante_id={job_id} total_etapas={len(etapas_actualizadas)}",
        )
        self.db.commit()

        return [
            EtapaResponse(
                id=e.id,
                job_posting_id=e.job_posting_id,
                stage_number=e.stage_number,
                name=e.name,
                description=e.description,
                is_terminal=e.is_terminal,
                total_candidatos=0,
            )
            for e in etapas_actualizadas
        ]

    def obtener_pipeline_vacante(
        self, user_id: uuid.UUID, job_id: uuid.UUID
    ) -> PipelineVacanteResponse:
        miembro = self._obtener_miembro(user_id)
        vacante = self.repo.obtener_vacante(job_id, miembro.company_id)
        if not vacante:
            raise NotFoundException("Vacante no encontrada o no pertenece a la empresa.")

        etapas = self.repo.obtener_etapas_vacante(job_id)
        apps = self.repo.obtener_postulaciones_vacante(job_id)

        conteo_por_etapa: dict[uuid.UUID, int] = {}
        candidatos_list: list[CandidatoPipelineItem] = []

        total = len(apps)
        descartados = 0
        contratados = 0

        for a in apps:
            if a.current_status == "rejected":
                descartados += 1
            elif a.current_status == "hired":
                contratados += 1

            if a.current_stage_id and a.current_status not in ("rejected", "withdrawn"):
                conteo_por_etapa[a.current_stage_id] = conteo_por_etapa.get(a.current_stage_id, 0) + 1

            cand: CandidateProfile = a.candidate
            user = cand.user if cand else None

            # Obtener carrera principal
            carrera_nombre = None
            if cand and cand.educations:
                for edu in cand.educations:
                    if edu.field_of_study:
                        carrera_nombre = edu.field_of_study.name
                        break
                    elif edu.program_name:
                        carrera_nombre = edu.program_name

            nombre_completo = f"{cand.first_name} {cand.last_name}" if cand else "Candidato"
            info_estado = ESTADOS_INFO.get(a.current_status, {"label": a.current_status.capitalize(), "color": "gray"})

            # Regla de negocio: si está descartado o retirado, no puede avanzar
            puede_avanzar = a.current_status not in ("rejected", "withdrawn", "hired")
            puede_descartar = a.current_status not in ("rejected", "withdrawn", "hired")

            candidatos_list.append(
                CandidatoPipelineItem(
                    postulacion_id=a.id,
                    candidato_id=cand.id if cand else uuid.uuid4(),
                    candidato_nombre=nombre_completo,
                    candidato_titular=cand.professional_headline if cand else None,
                    candidato_carrera=carrera_nombre,
                    candidato_email=user.email if user else None,
                    candidato_telefono=cand.phone if cand else None,
                    candidato_ciudad=cand.city if cand else None,
                    estado=a.current_status,
                    estado_label=info_estado["label"],
                    estado_color=info_estado["color"],
                    etapa_actual_id=a.current_stage_id,
                    etapa_actual_nombre=a.current_stage.name if a.current_stage else None,
                    etapa_actual_numero=a.current_stage.stage_number if a.current_stage else None,
                    fecha_postulacion=a.applied_at,
                    fecha_ultimo_cambio=a.updated_at or a.applied_at,
                    total_notas=len(a.notes) if a.notes else 0,
                    puede_avanzar=puede_avanzar,
                    puede_descartar=puede_descartar,
                )
            )

        activos = total - descartados - contratados

        vac_resumen = VacanteResumenSeleccion(
            id=vacante.id,
            titulo=vacante.title,
            seniority=vacante.seniority_level,
            modalidad=vacante.work_modality,
            modalidad_label=MODALIDADES_INFO.get(vacante.work_modality, "Presencial"),
            tipo_empleo=vacante.employment_type,
            tipo_empleo_label=TIPOS_EMPLEO_INFO.get(vacante.employment_type, "Tiempo Completo"),
            total_postulantes=total,
            total_activos=activos,
            total_descartados=descartados,
            total_contratados=contratados,
        )

        etapas_resp = [
            EtapaResponse(
                id=e.id,
                job_posting_id=e.job_posting_id,
                stage_number=e.stage_number,
                name=e.name,
                description=e.description,
                is_terminal=e.is_terminal,
                total_candidatos=conteo_por_etapa.get(e.id, 0),
            )
            for e in etapas
        ]

        return PipelineVacanteResponse(
            vacante=vac_resumen,
            etapas=etapas_resp,
            candidatos=candidatos_list,
        )

    def avanzar_etapa(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: AvanzarEtapaRequest,
        ip: str = "127.0.0.1",
    ) -> CandidatoPipelineItem:
        miembro = self._obtener_miembro(user_id)
        app = self.repo.obtener_postulacion_por_id(application_id)

        if not app or not app.job_posting or app.job_posting.company_id != miembro.company_id:
            raise NotFoundException("Postulación no encontrada o no pertenece a las vacantes de su empresa.")

        # Regla de negocio HU-17: Candidato descartado no puede volver a avanzar
        if app.current_status == "rejected":
            raise BadRequestException("Un candidato descartado no puede volver a avanzar en el mismo proceso.")
        if app.current_status == "withdrawn":
            raise BadRequestException("La postulación ha sido retirada por el candidato.")

        # Validar que la etapa pertenezca a la misma vacante
        etapas_vacante = self.repo.obtener_etapas_vacante(app.job_id)
        etapa_destino = next((e for e in etapas_vacante if e.id == data.stage_id), None)
        if not etapa_destino:
            raise BadRequestException("La etapa seleccionada no pertenece al proceso de esta vacante.")

        nuevo_status = self._inferir_status_por_etapa(etapa_destino)

        # Ejecutar avance en base de datos
        self.repo.avanzar_etapa_postulacion(
            application=app,
            nueva_etapa=etapa_destino,
            nuevo_status=nuevo_status,
            user_id=user_id,
            observacion=data.observacion,
        )

        # Disparar notificación automática al egresado (Criterio de Aceptación)
        empresa_nombre = miembro.company.trade_name or miembro.company.legal_name
        if app.candidate and app.candidate.user_id:
            self.repo.crear_notificacion(
                user_id=app.candidate.user_id,
                tipo="application_status",
                title=f"Avance en proceso: {app.job_posting.title}",
                cuerpo=f"¡Felicidades! Has avanzado a la etapa '{etapa_destino.name}' en el proceso de selección de {empresa_nombre}.",
                enlace=f"/postulaciones",
            )

        # Registro en bitácora
        self.bitacora.registrar(
            modulo="seleccion",
            accion="avanzar_etapa",
            usuario_id=user_id,
            ip=ip,
            detalles=f"postulacion_id={app.id} etapa_id={etapa_destino.id} etapa_nombre={etapa_destino.name} observacion={data.observacion or ''}",
        )
        self.db.commit()

        # Recargar datos y mapear
        app_refreshed = self.repo.obtener_postulacion_por_id(app.id)
        return self._mapear_candidato_item(app_refreshed)

    def descartar_candidato(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: DescartarCandidatoRequest,
        ip: str = "127.0.0.1",
    ) -> CandidatoPipelineItem:
        miembro = self._obtener_miembro(user_id)
        app = self.repo.obtener_postulacion_por_id(application_id)

        if not app or not app.job_posting or app.job_posting.company_id != miembro.company_id:
            raise NotFoundException("Postulación no encontrada o no pertenece a su empresa.")

        if app.current_status == "rejected":
            raise BadRequestException("El candidato ya se encuentra descartado.")

        # Ejecutar descarte
        self.repo.descartar_candidato_postulacion(
            application=app,
            user_id=user_id,
            motivo=data.motivo,
        )

        # Disparar notificación al egresado
        empresa_nombre = miembro.company.trade_name or miembro.company.legal_name
        if app.candidate and app.candidate.user_id:
            self.repo.crear_notificacion(
                user_id=app.candidate.user_id,
                tipo="application_status",
                title=f"Actualización de tu postulación: {app.job_posting.title}",
                cuerpo=f"Tu proceso de postulación a {app.job_posting.title} en {empresa_nombre} ha finalizado. Te agradecemos por tu interés y tiempo.",
                enlace=f"/postulaciones",
            )

        # Registro en bitácora
        self.bitacora.registrar(
            modulo="seleccion",
            accion="descartar_candidato",
            usuario_id=user_id,
            ip=ip,
            detalles=f"postulacion_id={app.id} motivo={data.motivo or ''}",
        )
        self.db.commit()

        app_refreshed = self.repo.obtener_postulacion_por_id(app.id)
        return self._mapear_candidato_item(app_refreshed)

    def agregar_nota_interna(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: NotaInternaRequest,
        ip: str = "127.0.0.1",
    ) -> NotaInternaResponse:
        miembro = self._obtener_miembro(user_id)
        app = self.repo.obtener_postulacion_por_id(application_id)

        if not app or not app.job_posting or app.job_posting.company_id != miembro.company_id:
            raise NotFoundException("Postulación no encontrada o no pertenece a su empresa.")

        nota = self.repo.crear_nota_interna(
            application_id=app.id,
            company_member_id=miembro.id,
            contenido=data.content,
        )

        self.bitacora.registrar(
            modulo="seleccion",
            accion="agregar_nota_interna",
            usuario_id=user_id,
            ip=ip,
            detalles=f"postulacion_id={app.id} nota_id={nota.id}",
        )
        self.db.commit()

        nombre_autor = miembro.user.email if miembro.user else "Miembro del equipo"
        return NotaInternaResponse(
            id=nota.id,
            postulacion_id=nota.application_id,
            autor_nombre=nombre_autor,
            autor_cargo=miembro.job_title,
            content=nota.content,
            created_at=nota.created_at,
        )

    def listar_notas_internas(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> list[NotaInternaResponse]:
        miembro = self._obtener_miembro(user_id)
        app = self.repo.obtener_postulacion_por_id(application_id)

        if not app or not app.job_posting or app.job_posting.company_id != miembro.company_id:
            raise NotFoundException("Postulación no encontrada o no pertenece a su empresa.")

        notas = self.repo.listar_notas_internas(application_id)
        resultado: list[NotaInternaResponse] = []
        for n in notas:
            user = n.member.user if n.member else None
            resultado.append(
                NotaInternaResponse(
                    id=n.id,
                    postulacion_id=n.application_id,
                    autor_nombre=user.email if user else "Miembro del equipo",
                    autor_cargo=n.member.job_title if n.member else None,
                    content=n.content,
                    created_at=n.created_at,
                )
            )
        return resultado

    def _mapear_candidato_item(self, a: Application) -> CandidatoPipelineItem:
        cand: CandidateProfile = a.candidate
        user = cand.user if cand else None

        carrera_nombre = None
        if cand and cand.educations:
            for edu in cand.educations:
                if edu.field_of_study:
                    carrera_nombre = edu.field_of_study.name
                    break
                elif edu.program_name:
                    carrera_nombre = edu.program_name

        nombre_completo = f"{cand.first_name} {cand.last_name}" if cand else "Candidato"
        info_estado = ESTADOS_INFO.get(a.current_status, {"label": a.current_status.capitalize(), "color": "gray"})

        return CandidatoPipelineItem(
            postulacion_id=a.id,
            candidato_id=cand.id if cand else uuid.uuid4(),
            candidato_nombre=nombre_completo,
            candidato_titular=cand.professional_headline if cand else None,
            candidato_carrera=carrera_nombre,
            candidato_email=user.email if user else None,
            candidato_telefono=cand.phone if cand else None,
            candidato_ciudad=cand.city if cand else None,
            estado=a.current_status,
            estado_label=info_estado["label"],
            estado_color=info_estado["color"],
            etapa_actual_id=a.current_stage_id,
            etapa_actual_nombre=a.current_stage.name if a.current_stage else None,
            etapa_actual_numero=a.current_stage.stage_number if a.current_stage else None,
            fecha_postulacion=a.applied_at,
            fecha_ultimo_cambio=a.updated_at or a.applied_at,
            total_notas=len(a.notes) if a.notes else 0,
            puede_avanzar=a.current_status not in ("rejected", "withdrawn", "hired"),
            puede_descartar=a.current_status not in ("rejected", "withdrawn", "hired"),
        )
