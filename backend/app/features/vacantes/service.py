import logging
import math
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import (
    BusinessException,
    ForbiddenException,
    ResourceNotFoundException,
)
from app.features.ia.services import afinidad as motor_afinidad
from app.features.moderacion import reglas as reglas_denuncias
from app.features.vacantes.repository import VacanteRepository
from app.features.vacantes.schema import (
    CriterioAfinidadResponse,
    CarreraEnVacanteResponse,
    EmpresaEnVacanteResponse,
    EstadisticasPublicasResponse,
    FiltrosDisponiblesResponse,
    HabilidadEnVacanteResponse,
    JobSkillItemResponse,
    PreguntaFiltroCreateRequest,
    PreguntaFiltroUpdateRequest,
    VacanteCambioEstadoRequest,
    VacanteCreateRequest,
    VacanteDetalleBusquedaResponse,
    VacantePaginadaResponse,
    VacanteResponse,
    VacanteResumenResponse,
    VacantesBuscadasResponse,
    VacanteUpdateRequest,
)
from app.models.candidato import CandidateProfile
from app.models.empresa import Company, CompanyMember
from app.models.institucion import CompanyInstitution
from app.models.seguridad import AuditLog
from app.models.vacante import JobPosting, JobSkill, JobStatus, ScreeningOption, ScreeningQuestion
from app.security.dependencies import CurrentUser
from app.security.tenant import empresa_habilitada_en, institucion_de_candidato
from app.shared.email_service import EmailService

logger = logging.getLogger(__name__)

# Tope de vacantes que se puntúan para ordenar la búsqueda por afinidad.
_MAX_VACANTES_POR_AFINIDAD = 500


class VacanteService:
    """Capa de lógica de negocio para la gestión y publicación de vacantes laborales."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = VacanteRepository(db)
        self.email_service = EmailService()
        # Id de la vacante que la última operación dejó publicada (estaba en otro estado),
        # para que el router avise a los egresados afines después de responder.
        self.vacante_publicada: uuid.UUID | None = None

    # ─── Helpers Privados ───────────────────────────────────────────────────

    def _anotar_si_se_publico(self, vacante: JobPosting, estado_anterior: str | None) -> None:
        if vacante.status == JobStatus.PUBLISHED.value and estado_anterior != JobStatus.PUBLISHED.value:
            self.vacante_publicada = vacante.id

    def _obtener_empresa_y_miembro_de_usuario(
        self, usuario_id: uuid.UUID
    ) -> tuple[Company, CompanyMember | None]:
        """Recupera la empresa y la membresía del usuario autenticado."""
        stmt = (
            select(Company, CompanyMember)
            .join(CompanyMember, CompanyMember.company_id == Company.id)
            .where(CompanyMember.user_id == usuario_id, CompanyMember.is_active.is_(True))
        )
        resultado = self.db.execute(stmt).first()

        if resultado is None:
            stmt_alt = select(Company).join(CompanyMember, CompanyMember.company_id == Company.id).where(CompanyMember.user_id == usuario_id)
            comp = self.db.scalar(stmt_alt)
            if comp is None:
                raise ForbiddenException("El usuario no tiene una empresa asociada para gestionar vacantes.")
            return comp, None

        empresa, miembro = resultado
        if empresa.account_status == "suspended":
            raise ForbiddenException("La empresa asociada se encuentra suspendida.")

        return empresa, miembro

    def _registrar_auditoria(
        self,
        usuario_id: uuid.UUID | None,
        action: str,
        entity_id: uuid.UUID | None,
        details: dict | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Registra eventos relevantes en la bitácora de auditoría."""
        log = AuditLog(
            user_id=usuario_id,
            action=action,
            entity_type="vacantes",
            entity_id=entity_id,
            result="success",
            ip_address=ip_address,
            details_json=details,
        )
        self.db.add(log)

    def _a_dto(self, vacante: JobPosting) -> VacanteResponse:
        """Mapea una entidad ORM JobPosting al esquema de respuesta VacanteResponse."""
        skills_dto = [
            JobSkillItemResponse(
                skill_id=js.skill_id,
                skill_name=js.skill.name if js.skill else None,
                importance=js.importance,
                min_proficiency=js.min_proficiency,
                weight=js.weight,
            )
            for js in (vacante.skills or [])
        ]

        company_name = None
        if vacante.company:
            company_name = vacante.company.trade_name or vacante.company.legal_name

        category_name = vacante.category.name if vacante.category else None

        return VacanteResponse(
            id=vacante.id,
            company_id=vacante.company_id,
            company_name=company_name,
            created_by=vacante.created_by,
            category_id=vacante.category_id,
            category_name=category_name,
            title=vacante.title,
            description=vacante.description,
            responsibilities_json=vacante.responsibilities_json,
            requirements_json=vacante.requirements_json,
            benefits_json=vacante.benefits_json,
            seniority_level=vacante.seniority_level,
            employment_type=vacante.employment_type,
            work_modality=vacante.work_modality,
            min_education_level=vacante.min_education_level,
            min_years_experience=vacante.min_years_experience,
            country_code=vacante.country_code,
            city=vacante.city,
            latitude=vacante.latitude,
            longitude=vacante.longitude,
            salary_min=vacante.salary_min,
            salary_max=vacante.salary_max,
            currency=vacante.currency,
            salary_visible=vacante.salary_visible,
            positions_available=vacante.positions_available,
            status=vacante.status,
            rejection_reason=vacante.rejection_reason,
            application_deadline=vacante.application_deadline,
            published_at=vacante.published_at,
            closed_at=vacante.closed_at,
            view_count=vacante.view_count,
            created_at=vacante.created_at,
            updated_at=vacante.updated_at,
            skills=skills_dto,
        )

    # ─── Casos de Uso ────────────────────────────────────────────────────────

    def crear_vacante(
        self,
        payload: VacanteCreateRequest,
        current_user: CurrentUser,
        ip_address: str | None = None,
    ) -> VacanteResponse:
        """Crea una nueva vacante aplicando reglas de verificación de empresa."""
        empresa, _miembro = self._obtener_empresa_y_miembro_de_usuario(current_user.id_usuario)

        # Regla de negocio: Si la empresa no está verificada, se fuerza el estado a DRAFT.
        # Si está verificada y pide publicar, pasa a revisión institucional (HU-12): no se
        # publica directo, salvo que quien crea sea un administrador de la plataforma.
        estado_final = payload.status.value
        published_at = None

        if empresa.verification_status != "verified":
            estado_final = JobStatus.DRAFT.value
        elif estado_final == JobStatus.PUBLISHED.value:
            if current_user.es_admin:
                published_at = datetime.now()
            else:
                estado_final = JobStatus.PENDING_REVIEW.value

        vacante = JobPosting(
            company_id=empresa.id,
            created_by=current_user.id_usuario,
            category_id=payload.category_id,
            title=payload.title.strip(),
            description=payload.description.strip(),
            responsibilities_json=payload.responsibilities_json,
            requirements_json=payload.requirements_json,
            benefits_json=payload.benefits_json,
            seniority_level=payload.seniority_level.value,
            employment_type=payload.employment_type.value,
            work_modality=payload.work_modality.value,
            min_education_level=payload.min_education_level,
            min_years_experience=payload.min_years_experience,
            country_code=payload.country_code,
            city=payload.city.strip(),
            latitude=payload.latitude,
            longitude=payload.longitude,
            salary_min=payload.salary_min,
            salary_max=payload.salary_max,
            currency=payload.currency,
            salary_visible=payload.salary_visible,
            positions_available=payload.positions_available,
            status=estado_final,
            published_at=published_at,
            application_deadline=payload.application_deadline,
        )

        skills = [
            JobSkill(
                skill_id=s.skill_id,
                importance=s.importance.value if s.importance else None,
                min_proficiency=s.min_proficiency.value if s.min_proficiency else None,
                weight=s.weight,
            )
            for s in payload.skills
        ]

        vacante_creada = self.repo.crear(vacante, skills)

        self._registrar_auditoria(
            usuario_id=current_user.id_usuario,
            action="create_job_posting",
            entity_id=vacante_creada.id,
            details={"title": vacante_creada.title, "status": vacante_creada.status},
            ip_address=ip_address,
        )
        self.db.commit()
        self._anotar_si_se_publico(vacante_creada, None)

        return self._a_dto(vacante_creada)

    def listar_mis_vacantes(
        self,
        current_user: CurrentUser,
        estado: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> VacantePaginadaResponse:
        """Lista las vacantes de la empresa asociada al usuario autenticado."""
        empresa, _ = self._obtener_empresa_y_miembro_de_usuario(current_user.id_usuario)
        items, total = self.repo.listar_por_empresa(
            company_id=empresa.id,
            estado=estado,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        ocultas = reglas_denuncias.vacantes_ocultas(self.db, [v.id for v in items])

        return VacantePaginadaResponse(
            items=[self._a_dto(v).model_copy(update={"oculta_por_denuncias": v.id in ocultas}) for v in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def listar_publicas(
        self,
        q: str | None = None,
        category_id: uuid.UUID | None = None,
        city: str | None = None,
        work_modality: str | None = None,
        seniority_level: str | None = None,
        employment_type: str | None = None,
        salary_min: Decimal | None = None,
        page: int = 1,
        page_size: int = 10,
        usuario_id: uuid.UUID | None = None,
    ) -> VacantePaginadaResponse:
        """Lista las vacantes publicadas activas con filtros para candidatos o público general.

        Un egresado autenticado solo ve vacantes de empresas habilitadas en su universidad.
        """
        items, total = self.repo.listar_publicas(
            institution_id=self._institucion_para_busqueda(usuario_id),
            q=q,
            category_id=category_id,
            city=city,
            work_modality=work_modality,
            seniority_level=seniority_level,
            employment_type=employment_type,
            salary_min=salary_min,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return VacantePaginadaResponse(
            items=[self._a_dto(v) for v in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def obtener_detalle(
        self,
        vacante_id: uuid.UUID,
        current_user: CurrentUser | None = None,
    ) -> VacanteResponse:
        """Obtiene el detalle de una vacante verificando visibilidad según estado y pertenencia."""
        vacante = self.repo.obtener_por_id(vacante_id)
        if vacante is None:
            raise ResourceNotFoundException("La vacante solicitada no existe.")

        if vacante.status == JobStatus.PUBLISHED.value and not reglas_denuncias.esta_oculta(self.db, vacante.id):
            institucion = self._institucion_para_busqueda(current_user.id_usuario if current_user else None)
            if institucion is not None and not empresa_habilitada_en(self.db, vacante.company_id, institucion):
                raise ResourceNotFoundException("La vacante solicitada no existe.")
            return self._a_dto(vacante)

        if current_user is None:
            raise ForbiddenException("No tiene permisos para consultar esta vacante.")

        if current_user.es_admin:
            return self._a_dto(vacante)

        empresa, _ = self._obtener_empresa_y_miembro_de_usuario(current_user.id_usuario)
        if vacante.company_id != empresa.id:
            raise ForbiddenException("No tiene permisos para consultar esta vacante.")

        return self._a_dto(vacante)

    def actualizar_vacante(
        self,
        vacante_id: uuid.UUID,
        payload: VacanteUpdateRequest,
        current_user: CurrentUser,
        ip_address: str | None = None,
    ) -> VacanteResponse:
        """Actualiza una vacante existente garantizando que pertenezca a la empresa del usuario."""
        vacante = self.repo.obtener_por_id(vacante_id)
        if vacante is None:
            raise ResourceNotFoundException("La vacante a editar no existe.")

        if current_user.es_admin:
            empresa = vacante.company
        else:
            empresa, _ = self._obtener_empresa_y_miembro_de_usuario(current_user.id_usuario)
            if vacante.company_id != empresa.id:
                raise ForbiddenException("No tiene permisos para modificar esta vacante.")

        estado_anterior = vacante.status
        datos_dict = payload.model_dump(exclude_unset=True, exclude={"skills", "status"})

        # Regla: Si se solicita publicar y la empresa no está verificada, rechazar.
        # Si esta verificada y quien edita no es admin, pasa a revision (HU-12) en vez
        # de publicarse directo.
        if payload.status is not None:
            nuevo_estado = payload.status.value
            if payload.status == JobStatus.PUBLISHED:
                if empresa.verification_status != "verified":
                    raise BusinessException(
                        "No se puede publicar la vacante porque la empresa aún se encuentra en revisión institucional."
                    )
                if current_user.es_admin:
                    if vacante.published_at is None:
                        datos_dict["published_at"] = datetime.now()
                else:
                    nuevo_estado = JobStatus.PENDING_REVIEW.value
            datos_dict["status"] = nuevo_estado

        for campo_enum in ("seniority_level", "employment_type", "work_modality"):
            if campo_enum in datos_dict and datos_dict[campo_enum] is not None:
                datos_dict[campo_enum] = datos_dict[campo_enum].value

        nuevas_skills = None
        if payload.skills is not None:
            nuevas_skills = [
                JobSkill(
                    skill_id=s.skill_id,
                    importance=s.importance.value if s.importance else None,
                    min_proficiency=s.min_proficiency.value if s.min_proficiency else None,
                    weight=s.weight,
                )
                for s in payload.skills
            ]

        vacante_actualizada = self.repo.actualizar(vacante, datos_dict, nuevas_skills)

        self._registrar_auditoria(
            usuario_id=current_user.id_usuario,
            action="update_job_posting",
            entity_id=vacante_id,
            details={"cambios": list(datos_dict.keys())},
            ip_address=ip_address,
        )
        self.db.commit()
        self._anotar_si_se_publico(vacante_actualizada, estado_anterior)

        return self._a_dto(vacante_actualizada)

    def cambiar_estado(
        self,
        vacante_id: uuid.UUID,
        payload: VacanteCambioEstadoRequest,
        current_user: CurrentUser,
        ip_address: str | None = None,
    ) -> VacanteResponse:
        """Transiciona el estado de la vacante (draft, published, paused, closed, archived)."""
        vacante = self.repo.obtener_por_id(vacante_id)
        if vacante is None:
            raise ResourceNotFoundException("La vacante no existe.")

        if current_user.es_admin:
            empresa = vacante.company
        else:
            empresa, _ = self._obtener_empresa_y_miembro_de_usuario(current_user.id_usuario)
            if vacante.company_id != empresa.id:
                raise ForbiddenException("No tiene permisos para cambiar el estado de esta vacante.")

        # Regla: Si se intenta publicar y la empresa no está verificada, rechazar.
        # Si esta verificada y quien pide el cambio no es admin, pasa a revision (HU-12).
        nuevo_estado = payload.status.value
        if payload.status == JobStatus.PUBLISHED:
            if empresa.verification_status != "verified":
                raise BusinessException(
                    "No se puede publicar la vacante. La empresa debe estar verificada por la UAGRM."
                )
            if not current_user.es_admin:
                nuevo_estado = JobStatus.PENDING_REVIEW.value

        estado_anterior = vacante.status
        vacante_modificada = self.repo.cambiar_estado(vacante, nuevo_estado)

        self._registrar_auditoria(
            usuario_id=current_user.id_usuario,
            action="change_job_status",
            entity_id=vacante_id,
            details={"nuevo_estado": nuevo_estado},
            ip_address=ip_address,
        )
        self.db.commit()
        self._anotar_si_se_publico(vacante_modificada, estado_anterior)

        return self._a_dto(vacante_modificada)

    # ─── Moderación institucional (HU-12) ───────────────────────────────────

    def listar_pendientes_revision(
        self,
        page: int = 1,
        page_size: int = 10,
        institution_id: uuid.UUID | None = None,
    ) -> VacantePaginadaResponse:
        """Lista las vacantes en estado 'pending_review' para que un moderador las revise.

        El moderador de una universidad solo revisa vacantes de empresas vinculadas a ella.
        """
        items, total = self.repo.listar_por_estado(
            JobStatus.PENDING_REVIEW.value, page=page, page_size=page_size, institution_id=institution_id
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return VacantePaginadaResponse(
            items=[self._a_dto(v) for v in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def moderar(
        self,
        vacante_id: uuid.UUID,
        aprobado: bool,
        motivo_rechazo: str | None,
        current_user: CurrentUser,
        ip_address: str | None = None,
        institution_id: uuid.UUID | None = None,
    ) -> VacanteResponse:
        """Aprueba o rechaza una vacante pendiente de revisión (HU-12).

        Al aprobar, la vacante pasa a 'published' y queda visible para los egresados.
        Al rechazar, vuelve a 'rejected' con el motivo, y la empresa es notificada para
        que pueda corregirla y reenviarla.
        """
        vacante = self.repo.obtener_por_id(vacante_id)
        if vacante is None or (
            institution_id is not None
            and self.db.get(CompanyInstitution, (vacante.company_id, institution_id)) is None
        ):
            raise ResourceNotFoundException("La vacante a moderar no existe.")

        if vacante.status != JobStatus.PENDING_REVIEW.value:
            raise BusinessException(
                f"Solo se pueden moderar vacantes en revisión (estado actual: '{vacante.status}')."
            )

        nuevo_estado = JobStatus.PUBLISHED.value if aprobado else JobStatus.REJECTED.value
        motivo = None if aprobado else motivo_rechazo

        vacante_moderada = self.repo.moderar(vacante, nuevo_estado, motivo)

        destinatario = vacante.company.contact_email if vacante.company else None
        if destinatario:
            if aprobado:
                self.email_service.enviar(
                    destinatario,
                    "Vacante aprobada",
                    f"Tu vacante '{vacante.title}' fue aprobada y ya está publicada en la plataforma.",
                )
            else:
                self.email_service.enviar(
                    destinatario,
                    "Vacante rechazada",
                    f"Tu vacante '{vacante.title}' fue rechazada. Motivo: {motivo}. "
                    "Podés corregirla y volver a enviarla a revisión.",
                )

        self._registrar_auditoria(
            usuario_id=current_user.id_usuario,
            action="moderate_job_posting",
            entity_id=vacante_id,
            details={"aprobado": aprobado, "motivo_rechazo": motivo},
            ip_address=ip_address,
        )
        self.db.commit()
        self._anotar_si_se_publico(vacante_moderada, JobStatus.PENDING_REVIEW.value)

        return self._a_dto(vacante_moderada)

    def eliminar_vacante(
        self,
        vacante_id: uuid.UUID,
        current_user: CurrentUser,
        ip_address: str | None = None,
    ) -> dict[str, str]:
        """Elimina una vacante si pertenece a la empresa solicitante."""
        vacante = self.repo.obtener_por_id(vacante_id)
        if vacante is None:
            raise ResourceNotFoundException("La vacante a eliminar no existe.")

        if current_user.es_admin:
            empresa = vacante.company
        else:
            empresa, _ = self._obtener_empresa_y_miembro_de_usuario(current_user.id_usuario)
            if vacante.company_id != empresa.id:
                raise ForbiddenException("No tiene permisos para eliminar esta vacante.")

        self.repo.eliminar(vacante)

        self._registrar_auditoria(
            usuario_id=current_user.id_usuario,
            action="delete_job_posting",
            entity_id=vacante_id,
            details={"title": vacante.title},
            ip_address=ip_address,
        )
        self.db.commit()

        return {"mensaje": "Vacante eliminada exitosamente."}

    # ─── Preguntas de filtro (screening) — HU-11 ────────────────────────────

    def _obtener_vacante_propia(self, vacante_id: uuid.UUID, current_user: CurrentUser) -> JobPosting:
        vacante = self.repo.obtener_por_id(vacante_id)
        if vacante is None:
            raise ResourceNotFoundException("La vacante no existe.")

        if not current_user.es_admin:
            empresa, _ = self._obtener_empresa_y_miembro_de_usuario(current_user.id_usuario)
            if vacante.company_id != empresa.id:
                raise ForbiddenException("No tiene permisos sobre esta vacante.")

        return vacante

    def _vacante_tiene_postulaciones(self, vacante_id: uuid.UUID) -> bool:
        from app.models.postulacion import Application

        return self.db.query(Application.id).filter(Application.job_id == vacante_id).first() is not None

    def listar_preguntas_filtro(self, vacante_id: uuid.UUID, current_user: CurrentUser) -> list[ScreeningQuestion]:
        self._obtener_vacante_propia(vacante_id, current_user)
        return (
            self.db.query(ScreeningQuestion)
            .filter(ScreeningQuestion.job_posting_id == vacante_id)
            .order_by(ScreeningQuestion.position)
            .all()
        )

    def crear_pregunta_filtro(
        self,
        vacante_id: uuid.UUID,
        payload: "PreguntaFiltroCreateRequest",
        current_user: CurrentUser,
    ) -> ScreeningQuestion:
        self._obtener_vacante_propia(vacante_id, current_user)

        pregunta = ScreeningQuestion(
            job_posting_id=vacante_id,
            question_text=payload.question_text,
            question_type=payload.question_type,
            is_required=payload.is_required,
            is_knockout=payload.is_knockout,
            position=payload.position,
        )
        self.db.add(pregunta)
        self.db.flush()

        opciones_creadas = []
        for opcion in payload.options:
            nueva_opcion = ScreeningOption(
                question_id=pregunta.id,
                option_text=opcion.option_text,
                is_accepted=opcion.is_accepted,
                position=opcion.position,
            )
            self.db.add(nueva_opcion)
            opciones_creadas.append(nueva_opcion)

        self.db.commit()
        self.db.refresh(pregunta)
        for opcion in opciones_creadas:
            self.db.refresh(opcion)
        pregunta.options = opciones_creadas
        return pregunta

    def actualizar_pregunta_filtro(
        self,
        vacante_id: uuid.UUID,
        pregunta_id: uuid.UUID,
        payload: "PreguntaFiltroUpdateRequest",
        current_user: CurrentUser,
    ) -> ScreeningQuestion:
        self._obtener_vacante_propia(vacante_id, current_user)

        if self._vacante_tiene_postulaciones(vacante_id):
            raise BusinessException(
                "No se puede modificar una pregunta de filtro de una vacante que ya tiene postulaciones."
            )

        pregunta = (
            self.db.query(ScreeningQuestion)
            .filter(ScreeningQuestion.id == pregunta_id, ScreeningQuestion.job_posting_id == vacante_id)
            .first()
        )
        if pregunta is None:
            raise ResourceNotFoundException("La pregunta de filtro no existe.")

        datos = payload.model_dump(exclude_unset=True, exclude={"options"})
        for campo, valor in datos.items():
            setattr(pregunta, campo, valor)

        opciones_actuales = None
        if payload.options is not None:
            self.db.query(ScreeningOption).filter(ScreeningOption.question_id == pregunta.id).delete()
            opciones_actuales = []
            for opcion in payload.options:
                nueva_opcion = ScreeningOption(
                    question_id=pregunta.id,
                    option_text=opcion.option_text,
                    is_accepted=opcion.is_accepted,
                    position=opcion.position,
                )
                self.db.add(nueva_opcion)
                opciones_actuales.append(nueva_opcion)

        self.db.commit()
        self.db.refresh(pregunta)

        if opciones_actuales is not None:
            for opcion in opciones_actuales:
                self.db.refresh(opcion)
            pregunta.options = opciones_actuales
        else:
            pregunta.options = (
                self.db.query(ScreeningOption)
                .filter(ScreeningOption.question_id == pregunta.id)
                .order_by(ScreeningOption.position)
                .all()
            )
        return pregunta

    def eliminar_pregunta_filtro(
        self,
        vacante_id: uuid.UUID,
        pregunta_id: uuid.UUID,
        current_user: CurrentUser,
    ) -> dict[str, str]:
        self._obtener_vacante_propia(vacante_id, current_user)

        if self._vacante_tiene_postulaciones(vacante_id):
            raise BusinessException(
                "No se puede eliminar una pregunta de filtro de una vacante que ya tiene postulaciones."
            )

        pregunta = (
            self.db.query(ScreeningQuestion)
            .filter(ScreeningQuestion.id == pregunta_id, ScreeningQuestion.job_posting_id == vacante_id)
            .first()
        )
        if pregunta is None:
            raise ResourceNotFoundException("La pregunta de filtro no existe.")

        self.db.delete(pregunta)
        self.db.commit()
        return {"mensaje": "Pregunta de filtro eliminada."}

    # ─── Búsqueda avanzada con afinidad — HU-13 ─────────────────────────────
    # Vive bajo /vacantes/buscar (separado de listar_publicas/GET /vacantes)
    # para no romper el contrato ya consumido por el listado web y la app móvil.

    def buscar_vacantes(
        self,
        q: str | None = None,
        carrera_id: uuid.UUID | None = None,
        categoria_id: uuid.UUID | None = None,
        ciudad: str | None = None,
        modalidad: str | None = None,
        jornada: str | None = None,
        seniority: str | None = None,
        salario_min: Decimal | None = None,
        salario_max: Decimal | None = None,
        ordenar_por: str = "fecha",
        limit: int = 20,
        offset: int = 0,
        usuario_id: uuid.UUID | None = None,
    ) -> VacantesBuscadasResponse:
        """Busca vacantes con filtros combinados y calcula la afinidad con el perfil del egresado si está autenticado."""
        perfil = self._perfil_afinidad_de(usuario_id)
        # Para ordenar por afinidad hay que puntuar todas las coincidencias, no solo la página.
        por_afinidad = ordenar_por == "afinidad" and perfil is not None
        items, total = self.repo.buscar_vacantes(
            q=q,
            carrera_id=carrera_id,
            categoria_id=categoria_id,
            ciudad=ciudad,
            modalidad=modalidad,
            jornada=jornada,
            seniority=seniority,
            salario_min=salario_min,
            salario_max=salario_max,
            solo_vigentes=True,
            ordenar_por=ordenar_por if ordenar_por != "afinidad" else "fecha",
            limit=_MAX_VACANTES_POR_AFINIDAD if por_afinidad else limit,
            offset=0 if por_afinidad else offset,
            institution_id=self._institucion_para_busqueda(usuario_id),
        )

        vacantes_dto = []
        for vacante in items:
            afinidad = self._calcular_afinidad(vacante, perfil)
            vacantes_dto.append(self._mapear_a_resumen_busqueda(vacante, afinidad.porcentaje if afinidad else None))

        if por_afinidad:
            vacantes_dto.sort(key=lambda x: (x.afinidad_porcentaje or 0), reverse=True)
            vacantes_dto = vacantes_dto[offset : offset + limit]

        return VacantesBuscadasResponse(total=total, limit=limit, offset=offset, items=vacantes_dto)

    def obtener_detalle_busqueda(
        self, vacante_id: uuid.UUID, usuario_id: uuid.UUID | None = None, es_staff: bool = False
    ) -> VacanteDetalleBusquedaResponse:
        """Obtiene el detalle enriquecido (afinidad, contacto de empresa) de una vacante publicada.

        Una vacante sin publicar, retirada u oculta por denuncias (HU-22) solo la ven su
        empresa y el staff; para el resto es como si no existiera.
        """
        vacante = self.repo.obtener_por_id_con_afinidad(vacante_id, self._institucion_para_busqueda(usuario_id))
        if not vacante:
            raise ResourceNotFoundException("La vacante solicitada no existe o no está disponible.")
        publica = vacante.status == JobStatus.PUBLISHED.value and not reglas_denuncias.esta_oculta(
            self.db, vacante.id
        )
        if not publica and not es_staff and not self._es_de_su_empresa(vacante, usuario_id):
            raise ResourceNotFoundException("La vacante solicitada no existe o no está disponible.")

        self.repo.incrementar_vistas(vacante_id)

        afinidad = self._calcular_afinidad(vacante, self._perfil_afinidad_de(usuario_id))

        resumen = self._mapear_a_resumen_busqueda(vacante, afinidad.porcentaje if afinidad else None)
        empresa = vacante.company

        return VacanteDetalleBusquedaResponse(
            **resumen.model_dump(),
            afinidad_criterios=(
                [CriterioAfinidadResponse(**vars(c)) for c in afinidad.criterios] if afinidad else None
            ),
            responsibilities=vacante.responsibilities_json if isinstance(vacante.responsibilities_json, list) else [],
            requirements=vacante.requirements_json if isinstance(vacante.requirements_json, list) else [],
            benefits=vacante.benefits_json if isinstance(vacante.benefits_json, list) else [],
            # CP04 (HU-34): La información de contacto de la empresa es confidencial y solo se
            # expone si el usuario está autenticado en la plataforma.
            company_contact_email=empresa.contact_email if (empresa and usuario_id) else None,
            company_phone=empresa.phone if (empresa and usuario_id) else None,
            company_address=empresa.address if (empresa and usuario_id) else None,
        )

    def obtener_filtros_disponibles(self) -> FiltrosDisponiblesResponse:
        """Obtiene las opciones disponibles para los filtros de búsqueda."""
        return FiltrosDisponiblesResponse(**self.repo.obtener_filtros_disponibles())

    def obtener_estadisticas_publicas(self) -> EstadisticasPublicasResponse:
        """Obtiene estadísticas agregadas públicas con caché de 24 horas (HU-34)."""
        stats = self.repo.obtener_estadisticas_agregadas()
        return EstadisticasPublicasResponse(**stats)

    def _es_de_su_empresa(self, vacante: JobPosting, usuario_id: uuid.UUID | None) -> bool:
        if usuario_id is None:
            return False
        return (
            self.db.scalar(
                select(CompanyMember.user_id).where(
                    CompanyMember.user_id == usuario_id,
                    CompanyMember.company_id == vacante.company_id,
                    CompanyMember.is_active.is_(True),
                )
            )
            is not None
        )

    def _institucion_para_busqueda(self, usuario_id: uuid.UUID | None) -> uuid.UUID | None:
        """Universidad del egresado autenticado; None (sin filtro) para anónimos, empresas y staff."""
        return institucion_de_candidato(self.db, usuario_id) if usuario_id else None

    def _perfil_afinidad_de(self, usuario_id: uuid.UUID | None) -> motor_afinidad.PerfilAfinidad | None:
        """Perfil de afinidad del egresado autenticado; None si no es egresado o la IA está apagada."""
        if not usuario_id or not motor_afinidad.ia_activa():
            return None
        candidato_id = self.db.scalar(select(CandidateProfile.id).where(CandidateProfile.user_id == usuario_id))
        if candidato_id is None:
            return None
        try:
            return motor_afinidad.perfiles_de_candidatos(self.db, {candidato_id})[candidato_id]
        except Exception:
            # Si la IA falla, la búsqueda sigue funcionando sin afinidad (HU-23, CP04).
            logger.exception("No se pudo cargar el perfil de afinidad del usuario %s", usuario_id)
            return None

    @staticmethod
    def _calcular_afinidad(
        vacante: JobPosting, perfil: motor_afinidad.PerfilAfinidad | None
    ) -> motor_afinidad.Afinidad | None:
        """Afinidad del motor de la HU-23 (carrera, habilidades, experiencia e idiomas)."""
        if perfil is None:
            return None
        try:
            return motor_afinidad.evaluar(vacante, perfil)
        except Exception:
            logger.exception("No se pudo calcular la afinidad de la vacante %s", vacante.id)
            return None

    def _mapear_a_resumen_busqueda(self, vacante: JobPosting, afinidad: int | None = None) -> VacanteResumenResponse:
        empresa = vacante.company
        empresa_dto = EmpresaEnVacanteResponse(
            id=empresa.id,
            legal_name=empresa.legal_name,
            trade_name=empresa.trade_name,
            city=empresa.city,
            sector_name=empresa.sector.name if empresa.sector else None,
            website=empresa.website,
            description=empresa.description,
        )

        skills_dto = [
            HabilidadEnVacanteResponse(
                skill_id=js.skill_id,
                name=js.skill.name if js.skill else "",
                importance=js.importance or "required",
                min_proficiency=js.min_proficiency,
            )
            for js in vacante.skills
            if js.skill
        ]

        carreras_dto = [
            CarreraEnVacanteResponse(
                field_of_study_id=ep.field_of_study_id,
                name=ep.field_of_study.name if ep.field_of_study else "",
                education_level=ep.education_level,
                is_required=ep.is_required,
            )
            for ep in vacante.education_preferences
            if ep.field_of_study
        ]

        return VacanteResumenResponse(
            id=vacante.id,
            company=empresa_dto,
            category_id=vacante.category_id,
            category_name=vacante.category.name if vacante.category else None,
            title=vacante.title,
            description=vacante.description,
            seniority_level=vacante.seniority_level,
            employment_type=vacante.employment_type,
            work_modality=vacante.work_modality,
            country_code=vacante.country_code,
            city=vacante.city,
            salary_min=vacante.salary_min if vacante.salary_visible else None,
            salary_max=vacante.salary_max if vacante.salary_visible else None,
            currency=vacante.currency if vacante.salary_visible else None,
            salary_visible=vacante.salary_visible,
            positions_available=vacante.positions_available,
            status=vacante.status,
            min_education_level=vacante.min_education_level,
            min_years_experience=vacante.min_years_experience,
            application_deadline=vacante.application_deadline,
            published_at=vacante.published_at,
            view_count=vacante.view_count,
            skills=skills_dto,
            education_preferences=carreras_dto,
            afinidad_porcentaje=afinidad,
        )
