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
    JobSkillItemResponse,
    VacanteCambioEstadoRequest,
    VacanteCreateRequest,
    VacantePaginadaResponse,
    VacanteResponse,
    VacanteUpdateRequest,
)
from app.models.empresa import Company, CompanyMember
from app.models.seguridad import AuditLog
from app.models.vacante import JobPosting, JobSkill, JobStatus
from app.security.dependencies import CurrentUser


class VacanteService:
    """Capa de lógica de negocio para la gestión y publicación de vacantes laborales."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = VacanteRepository(db)

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
            # Búsqueda alternativa por si el usuario es owner directo sin fila activa en company_member
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
                required_level=js.required_level,
                is_required=js.is_required,
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
            created_by_member_id=vacante.created_by_member_id,
            category_id=vacante.category_id,
            category_name=category_name,
            title=vacante.title,
            description=vacante.description,
            responsibilities=vacante.responsibilities,
            requirements=vacante.requirements,
            seniority_level=vacante.seniority_level,
            employment_type=vacante.employment_type,
            work_modality=vacante.work_modality,
            minimum_education_level=vacante.minimum_education_level,
            required_experience_years=vacante.required_experience_years,
            country_code=vacante.country_code,
            city=vacante.city,
            location_text=vacante.location_text,
            latitude=vacante.latitude,
            longitude=vacante.longitude,
            salary_min=vacante.salary_min,
            salary_max=vacante.salary_max,
            currency=vacante.currency,
            salary_visible=vacante.salary_visible,
            positions_count=vacante.positions_count,
            status=vacante.status,
            published_at=vacante.published_at,
            closes_at=vacante.closes_at,
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
        empresa, miembro = self._obtener_empresa_y_miembro_de_usuario(current_user.id_usuario)

        # Regla de negocio: Si la empresa no está verificada, se fuerza el estado a DRAFT
        estado_final = payload.status.value
        published_at = None

        if empresa.verification_status != "verified":
            estado_final = JobStatus.DRAFT.value
        elif estado_final == JobStatus.PUBLISHED.value:
            published_at = datetime.now()

        vacante = JobPosting(
            company_id=empresa.id,
            created_by_member_id=miembro.id if miembro else None,
            category_id=payload.category_id,
            title=payload.title.strip(),
            description=payload.description.strip(),
            responsibilities=payload.responsibilities.strip() if payload.responsibilities else None,
            requirements=payload.requirements.strip() if payload.requirements else None,
            seniority_level=payload.seniority_level.value if payload.seniority_level else None,
            employment_type=payload.employment_type.value if payload.employment_type else None,
            work_modality=payload.work_modality.value if payload.work_modality else None,
            minimum_education_level=payload.minimum_education_level,
            required_experience_years=payload.required_experience_years,
            country_code=payload.country_code,
            city=payload.city.strip() if payload.city else None,
            location_text=payload.location_text.strip() if payload.location_text else None,
            latitude=payload.latitude,
            longitude=payload.longitude,
            salary_min=payload.salary_min,
            salary_max=payload.salary_max,
            currency=payload.currency,
            salary_visible=payload.salary_visible,
            positions_count=payload.positions_count,
            status=estado_final,
            published_at=published_at,
            closes_at=payload.closes_at,
        )

        skills = [
            JobSkill(
                skill_id=s.skill_id,
                required_level=s.required_level.value if s.required_level else None,
                is_required=s.is_required,
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

        # Si está publicada, cualquiera puede verla
        if vacante.status == JobStatus.PUBLISHED.value:
            return self._a_dto(vacante)

        # Si no está publicada (borrador, pausada, cerrada), validar permisos de autor o admin
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

        empresa, _ = self._obtener_empresa_y_miembro_de_usuario(current_user.id_usuario)
        if vacante.company_id != empresa.id and not current_user.es_admin:
            raise ForbiddenException("No tiene permisos para modificar esta vacante.")

        datos_dict = payload.model_dump(exclude_unset=True, exclude={"skills", "status"})

        # Regla: Si se solicita publicar y la empresa no está verificada, rechazar
        if payload.status is not None:
            if payload.status == JobStatus.PUBLISHED and empresa.verification_status != "verified":
                raise BusinessException(
                    "No se puede publicar la vacante porque la empresa aún se encuentra en revisión institucional."
                )
            datos_dict["status"] = payload.status.value
            if payload.status == JobStatus.PUBLISHED and vacante.published_at is None:
                datos_dict["published_at"] = datetime.now()

        # Transformar enums a strings en el diccionario
        for campo_enum in ("seniority_level", "employment_type", "work_modality"):
            if campo_enum in datos_dict and datos_dict[campo_enum] is not None:
                datos_dict[campo_enum] = datos_dict[campo_enum].value

        nuevas_skills = None
        if payload.skills is not None:
            nuevas_skills = [
                JobSkill(
                    skill_id=s.skill_id,
                    required_level=s.required_level.value if s.required_level else None,
                    is_required=s.is_required,
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
        """Transiciona el estado de la vacante (draft, published, paused, closed)."""
        vacante = self.repo.obtener_por_id(vacante_id)
        if vacante is None:
            raise ResourceNotFoundException("La vacante no existe.")

        empresa, _ = self._obtener_empresa_y_miembro_de_usuario(current_user.id_usuario)
        if vacante.company_id != empresa.id and not current_user.es_admin:
            raise ForbiddenException("No tiene permisos para cambiar el estado de esta vacante.")

        # Regla: Si se intenta publicar y la empresa no está verificada, rechazar
        if payload.status == JobStatus.PUBLISHED and empresa.verification_status != "verified":
            raise BusinessException(
                "No se puede publicar la vacante. La empresa debe estar verificada por la UAGRM."
            )

        vacante_modificada = self.repo.cambiar_estado(vacante, payload.status.value)

        self._registrar_auditoria(
            usuario_id=current_user.id_usuario,
            action="change_job_status",
            entity_id=vacante_id,
            details={"nuevo_estado": payload.status.value},
            ip_address=ip_address,
        )
        self.db.commit()

        return self._a_dto(vacante_modificada)

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

        empresa, _ = self._obtener_empresa_y_miembro_de_usuario(current_user.id_usuario)
        if vacante.company_id != empresa.id and not current_user.es_admin:
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
