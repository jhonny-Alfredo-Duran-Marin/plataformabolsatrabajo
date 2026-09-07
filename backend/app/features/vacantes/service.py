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
from app.features.vacantes.repository import VacanteRepository
from app.features.vacantes.schema import (
    CarreraEnVacanteResponse,
    EmpresaEnVacanteResponse,
    FiltrosDisponiblesResponse,
    HabilidadEnVacanteResponse,
    JobSkillItemResponse,
    VacanteCambioEstadoRequest,
    VacanteCreateRequest,
    VacanteDetalleBusquedaResponse,
    VacantePaginadaResponse,
    VacanteResponse,
    VacanteResumenResponse,
    VacantesBuscadasResponse,
    VacanteUpdateRequest,
)
from app.models.candidato import CandidateEducation, CandidateProfile, CandidateSkill
from app.models.empresa import Company, CompanyMember
from app.models.seguridad import AuditLog
from app.models.vacante import JobPosting, JobSkill, JobStatus
from app.security.dependencies import CurrentUser
from app.shared.email_service import EmailService


class VacanteService:
    """Capa de lógica de negocio para la gestión y publicación de vacantes laborales."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = VacanteRepository(db)
        self.email_service = EmailService()

    # ─── Helpers Privados ───────────────────────────────────────────────────

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

        return VacantePaginadaResponse(
            items=[self._a_dto(v) for v in items],
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
    ) -> VacantePaginadaResponse:
        """Lista las vacantes publicadas activas con filtros para candidatos o público general."""
        items, total = self.repo.listar_publicas(
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

        if vacante.status == JobStatus.PUBLISHED.value:
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

        vacante_modificada = self.repo.cambiar_estado(vacante, nuevo_estado)

        self._registrar_auditoria(
            usuario_id=current_user.id_usuario,
            action="change_job_status",
            entity_id=vacante_id,
            details={"nuevo_estado": nuevo_estado},
            ip_address=ip_address,
        )
        self.db.commit()

        return self._a_dto(vacante_modificada)

    # ─── Moderación institucional (HU-12) ───────────────────────────────────

    def listar_pendientes_revision(
        self,
        page: int = 1,
        page_size: int = 10,
    ) -> VacantePaginadaResponse:
        """Lista las vacantes en estado 'pending_review' para que un moderador las revise."""
        items, total = self.repo.listar_por_estado(
            JobStatus.PENDING_REVIEW.value, page=page, page_size=page_size
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
    ) -> VacanteResponse:
        """Aprueba o rechaza una vacante pendiente de revisión (HU-12).

        Al aprobar, la vacante pasa a 'published' y queda visible para los egresados.
        Al rechazar, vuelve a 'rejected' con el motivo, y la empresa es notificada para
        que pueda corregirla y reenviarla.
        """
        vacante = self.repo.obtener_por_id(vacante_id)
        if vacante is None:
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
            limit=limit,
            offset=offset,
        )

        candidato_skills, candidato_carreras, es_candidato = self._perfil_afinidad_de(usuario_id)

        vacantes_dto = []
        for vacante in items:
            afinidad = self._calcular_afinidad(vacante, candidato_skills, candidato_carreras) if es_candidato else None
            vacantes_dto.append(self._mapear_a_resumen_busqueda(vacante, afinidad))

        if ordenar_por == "afinidad" and es_candidato:
            vacantes_dto.sort(key=lambda x: (x.afinidad_porcentaje or 0), reverse=True)

        return VacantesBuscadasResponse(total=total, limit=limit, offset=offset, items=vacantes_dto)

    def obtener_detalle_busqueda(
        self, vacante_id: uuid.UUID, usuario_id: uuid.UUID | None = None
    ) -> VacanteDetalleBusquedaResponse:
        """Obtiene el detalle enriquecido (afinidad, contacto de empresa) de una vacante publicada."""
        vacante = self.repo.obtener_por_id_con_afinidad(vacante_id)
        if not vacante:
            raise ResourceNotFoundException("La vacante solicitada no existe o no está disponible.")

        self.repo.incrementar_vistas(vacante_id)

        candidato_skills, candidato_carreras, es_candidato = self._perfil_afinidad_de(usuario_id)
        afinidad = self._calcular_afinidad(vacante, candidato_skills, candidato_carreras) if es_candidato else None

        resumen = self._mapear_a_resumen_busqueda(vacante, afinidad)
        empresa = vacante.company

        return VacanteDetalleBusquedaResponse(
            **resumen.model_dump(),
            responsibilities=vacante.responsibilities_json if isinstance(vacante.responsibilities_json, list) else [],
            requirements=vacante.requirements_json if isinstance(vacante.requirements_json, list) else [],
            benefits=vacante.benefits_json if isinstance(vacante.benefits_json, list) else [],
            company_contact_email=empresa.contact_email if empresa else None,
            company_phone=empresa.phone if empresa else None,
            company_address=empresa.address if empresa else None,
        )

    def obtener_filtros_disponibles(self) -> FiltrosDisponiblesResponse:
        """Obtiene las opciones disponibles para los filtros de búsqueda."""
        return FiltrosDisponiblesResponse(**self.repo.obtener_filtros_disponibles())

    def _perfil_afinidad_de(
        self, usuario_id: uuid.UUID | None
    ) -> tuple[set[uuid.UUID], set[uuid.UUID], bool]:
        if not usuario_id:
            return set(), set(), False

        perfil = self.db.query(CandidateProfile).filter(CandidateProfile.user_id == usuario_id).one_or_none()
        if not perfil:
            return set(), set(), False

        skills = {
            cs.skill_id for cs in self.db.query(CandidateSkill).filter(CandidateSkill.candidate_id == perfil.id).all()
        }
        carreras = {
            ce.field_of_study_id
            for ce in self.db.query(CandidateEducation)
            .filter(CandidateEducation.candidate_id == perfil.id, CandidateEducation.field_of_study_id.isnot(None))
            .all()
        }
        return skills, carreras, True

    def _calcular_afinidad(
        self,
        vacante: JobPosting,
        candidato_skills: set[uuid.UUID],
        candidato_carreras: set[uuid.UUID],
    ) -> int:
        """Calcula el porcentaje de afinidad (0-100%) entre el candidato y la vacante."""
        score = 0
        total_peso = 0

        carreras_vacante = {ep.field_of_study_id for ep in vacante.education_preferences}
        if carreras_vacante:
            total_peso += 40
            if candidato_carreras & carreras_vacante:
                score += 40
        else:
            score += 20
            total_peso += 20

        skills_vacante = {js.skill_id for js in vacante.skills}
        if skills_vacante:
            total_peso += 60
            coincidencias = len(candidato_skills & skills_vacante)
            score += int((coincidencias / len(skills_vacante)) * 60)
        else:
            score += 30
            total_peso += 30

        if total_peso == 0:
            return 50

        return max(15, min(98, int((score / total_peso) * 100)))

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
