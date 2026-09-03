import uuid
from decimal import Decimal
from sqlalchemy import distinct, func, or_, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.catalogo import FieldOfStudy, JobCategory
from app.models.oferta import JobEducationPreference, JobPosting, JobSkill


class VacanteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

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
        solo_vigentes: bool = True,
        ordenar_por: str = "fecha",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[JobPosting], int]:
        """Busca vacantes aplicando filtros combinados y paginación."""
        stmt = select(JobPosting).where(JobPosting.status == "published")

        if solo_vigentes:
            now = func.now()
            stmt = stmt.where(
                or_(
                    JobPosting.application_deadline.is_(None),
                    JobPosting.application_deadline >= now,
                )
            )

        if q and q.strip():
            palabra = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    JobPosting.title.ilike(palabra),
                    JobPosting.description.ilike(palabra),
                )
            )

        if categoria_id:
            stmt = stmt.where(JobPosting.category_id == categoria_id)

        if ciudad and ciudad.strip():
            stmt = stmt.where(JobPosting.city.ilike(ciudad.strip()))

        if modalidad and modalidad.strip():
            stmt = stmt.where(JobPosting.work_modality == modalidad.strip())

        if jornada and jornada.strip():
            stmt = stmt.where(JobPosting.employment_type == jornada.strip())

        if seniority and seniority.strip():
            stmt = stmt.where(JobPosting.seniority_level == seniority.strip())

        if salario_min is not None:
            stmt = stmt.where(
                or_(
                    JobPosting.salary_max >= salario_min,
                    JobPosting.salary_min >= salario_min,
                )
            )

        if salario_max is not None:
            stmt = stmt.where(
                or_(
                    JobPosting.salary_min <= salario_max,
                    JobPosting.salary_max <= salario_max,
                )
            )

        if carrera_id:
            stmt = stmt.join(
                JobEducationPreference,
                JobEducationPreference.job_posting_id == JobPosting.id,
            ).where(JobEducationPreference.field_of_study_id == carrera_id)

        # Conteo total de resultados
        subq = stmt.subquery()
        count_stmt = select(func.count(distinct(subq.c.id)))
        total = self.db.scalar(count_stmt) or 0

        # Ordenamiento y relaciones
        if ordenar_por == "fecha":
            stmt = stmt.order_by(
                JobPosting.published_at.desc().nullslast(),
                JobPosting.created_at.desc(),
            )
        else:
            stmt = stmt.order_by(JobPosting.created_at.desc())

        stmt = (
            stmt.options(
                joinedload(JobPosting.company),
                joinedload(JobPosting.category),
                selectinload(JobPosting.skills).joinedload(JobSkill.skill),
                selectinload(JobPosting.education_preferences).joinedload(JobEducationPreference.field_of_study),
            )
            .limit(limit)
            .offset(offset)
        )

        items = list(self.db.scalars(stmt).unique())
        return items, total

    def obtener_por_id(self, vacante_id: uuid.UUID) -> JobPosting | None:
        """Obtiene una vacante por su ID con todas sus relaciones cargadas."""
        stmt = (
            select(JobPosting)
            .where(JobPosting.id == vacante_id)
            .options(
                joinedload(JobPosting.company),
                joinedload(JobPosting.category),
                selectinload(JobPosting.skills).joinedload(JobSkill.skill),
                selectinload(JobPosting.education_preferences).joinedload(JobEducationPreference.field_of_study),
            )
        )
        return self.db.scalar(stmt)

    def incrementar_vistas(self, vacante_id: uuid.UUID) -> None:
        """Incrementa el contador de vistas de una vacante."""
        self.db.execute(
            update(JobPosting)
            .where(JobPosting.id == vacante_id)
            .values(view_count=JobPosting.view_count + 1)
        )
        self.db.commit()

    def obtener_filtros_disponibles(self) -> dict:
        """Obtiene las opciones disponibles para los filtros de búsqueda."""
        base_published = select(JobPosting).where(JobPosting.status == "published")

        ciudades = list(
            self.db.scalars(
                select(distinct(JobPosting.city))
                .where(JobPosting.status == "published", JobPosting.city.isnot(None))
                .order_by(JobPosting.city)
            )
        )

        modalidades = list(
            self.db.scalars(
                select(distinct(JobPosting.work_modality))
                .where(JobPosting.status == "published")
                .order_by(JobPosting.work_modality)
            )
        )

        jornadas = list(
            self.db.scalars(
                select(distinct(JobPosting.employment_type))
                .where(JobPosting.status == "published")
                .order_by(JobPosting.employment_type)
            )
        )

        seniorities = list(
            self.db.scalars(
                select(distinct(JobPosting.seniority_level))
                .where(JobPosting.status == "published")
                .order_by(JobPosting.seniority_level)
            )
        )

        # Categorías y Carreras
        categorias = list(
            self.db.scalars(
                select(JobCategory).where(JobCategory.is_active.is_(True)).order_by(JobCategory.name)
            )
        )

        carreras = list(
            self.db.scalars(
                select(FieldOfStudy).order_by(FieldOfStudy.name)
            )
        )

        salarios = self.db.execute(
            select(
                func.min(JobPosting.salary_min),
                func.max(JobPosting.salary_max),
            ).where(JobPosting.status == "published", JobPosting.salary_visible.is_(True))
        ).fetchone()

        salario_min = salarios[0] if salarios else None
        salario_max = salarios[1] if salarios else None

        return {
            "ciudades": [c for c in ciudades if c],
            "modalidades": [m for m in modalidades if m],
            "jornadas": [j for j in jornadas if j],
            "niveles_experiencia": [s for s in seniorities if s],
            "categorias": [{"id": cat.id, "name": cat.name} for cat in categorias],
            "carreras": [{"id": car.id, "name": car.name, "category": car.category} for car in carreras],
            "salario_min_disponible": salario_min,
            "salario_max_disponible": salario_max,
        }

