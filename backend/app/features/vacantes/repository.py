import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalogo import JobCategory, Skill
from app.models.empresa import Company, CompanyMember
from app.models.vacante import JobPosting, JobSkill, JobStatus


class VacanteRepository:
    """Acceso a datos y persistencia para ofertas laborales y habilidades asociadas."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _query_base_con_relaciones(self):
        """Retorna la consulta base precargando todas las relaciones necesarias."""
        return select(JobPosting).options(
            selectinload(JobPosting.company),
            selectinload(JobPosting.created_by_member),
            selectinload(JobPosting.category),
            selectinload(JobPosting.skills).selectinload(JobSkill.skill),
        )

    def crear(self, vacante: JobPosting, skills: list[JobSkill] | None = None) -> JobPosting:
        """Persiste una nueva vacante y sus habilidades en la base de datos."""
        self.db.add(vacante)
        self.db.flush()

        if skills:
            for item in skills:
                item.job_id = vacante.id
                self.db.add(item)
            self.db.flush()

        return self.obtener_por_id(vacante.id) or vacante

    def obtener_por_id(self, vacante_id: uuid.UUID) -> JobPosting | None:
        """Obtiene una vacante por su ID con todas sus relaciones cargadas."""
        stmt = self._query_base_con_relaciones().where(JobPosting.id == vacante_id)
        return self.db.scalar(stmt)

    def listar_por_empresa(
        self,
        company_id: uuid.UUID,
        estado: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[JobPosting], int]:
        """Lista las vacantes de una empresa específica con paginación y filtro opcional de estado."""
        stmt = self._query_base_con_relaciones().where(JobPosting.company_id == company_id)
        count_stmt = select(func.count(JobPosting.id)).where(JobPosting.company_id == company_id)

        if estado:
            stmt = stmt.where(JobPosting.status == estado)
            count_stmt = count_stmt.where(JobPosting.status == estado)

        total = self.db.scalar(count_stmt) or 0
        offset = (max(page, 1) - 1) * page_size

        stmt = stmt.order_by(JobPosting.created_at.desc()).offset(offset).limit(page_size)
        items = list(self.db.scalars(stmt))

        return items, total

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
    ) -> tuple[list[JobPosting], int]:
        """Lista vacantes publicadas para búsqueda pública o de candidatos."""
        stmt = self._query_base_con_relaciones().where(JobPosting.status == JobStatus.PUBLISHED.value)
        count_stmt = select(func.count(JobPosting.id)).where(JobPosting.status == JobStatus.PUBLISHED.value)

        # Filtro de texto libre (título o descripción)
        if q:
            filtro_texto = or_(
                JobPosting.title.ilike(f"%{q.strip()}%"),
                JobPosting.description.ilike(f"%{q.strip()}%"),
            )
            stmt = stmt.where(filtro_texto)
            count_stmt = count_stmt.where(filtro_texto)

        # Filtros estructurados
        if category_id:
            stmt = stmt.where(JobPosting.category_id == category_id)
            count_stmt = count_stmt.where(JobPosting.category_id == category_id)

        if city:
            stmt = stmt.where(JobPosting.city.ilike(f"%{city.strip()}%"))
            count_stmt = count_stmt.where(JobPosting.city.ilike(f"%{city.strip()}%"))

        if work_modality:
            stmt = stmt.where(JobPosting.work_modality == work_modality)
            count_stmt = count_stmt.where(JobPosting.work_modality == work_modality)

        if seniority_level:
            stmt = stmt.where(JobPosting.seniority_level == seniority_level)
            count_stmt = count_stmt.where(JobPosting.seniority_level == seniority_level)

        if employment_type:
            stmt = stmt.where(JobPosting.employment_type == employment_type)
            count_stmt = count_stmt.where(JobPosting.employment_type == employment_type)

        if salary_min is not None:
            # Vacantes cuyo salario máximo sea al menos el solicitado o sin límite especificado
            filtro_salario = or_(
                JobPosting.salary_max >= salary_min,
                JobPosting.salary_min >= salary_min,
            )
            stmt = stmt.where(filtro_salario)
            count_stmt = count_stmt.where(filtro_salario)

        total = self.db.scalar(count_stmt) or 0
        offset = (max(page, 1) - 1) * page_size

        stmt = stmt.order_by(JobPosting.published_at.desc().nullslast(), JobPosting.created_at.desc())
        stmt = stmt.offset(offset).limit(page_size)
        items = list(self.db.scalars(stmt))

        return items, total

    def actualizar(
        self,
        vacante: JobPosting,
        datos: dict,
        nuevas_skills: list[JobSkill] | None = None,
    ) -> JobPosting:
        """Aplica una actualización parcial a la vacante y reemplaza sus habilidades si se suministran."""
        for clave, valor in datos.items():
            if hasattr(vacante, clave) and valor is not None:
                setattr(vacante, clave, valor)

        vacante.updated_at = datetime.now()

        # Si se envían nuevas habilidades, se reemplazan atómicamente
        if nuevas_skills is not None:
            self.db.execute(delete(JobSkill).where(JobSkill.job_id == vacante.id))
            for item in nuevas_skills:
                item.job_id = vacante.id
                self.db.add(item)

        self.db.flush()
        return self.obtener_por_id(vacante.id) or vacante

    def cambiar_estado(
        self,
        vacante: JobPosting,
        nuevo_estado: str,
        published_at: datetime | None = None,
    ) -> JobPosting:
        """Actualiza el estado del ciclo de vida de la vacante."""
        vacante.status = nuevo_estado
        if nuevo_estado == JobStatus.PUBLISHED.value and vacante.published_at is None:
            vacante.published_at = published_at or datetime.now()
        vacante.updated_at = datetime.now()
        self.db.flush()
        return vacante

    def eliminar(self, vacante: JobPosting) -> bool:
        """Elimina físicamente la vacante y sus habilidades dependientes en cascada."""
        self.db.delete(vacante)
        self.db.flush()
        return True
