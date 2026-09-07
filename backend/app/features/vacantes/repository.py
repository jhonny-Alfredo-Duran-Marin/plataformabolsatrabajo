import time
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, distinct, func, or_, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.catalogo import FieldOfStudy, JobCategory
from app.models.vacante import JobEducationPreference, JobPosting, JobSkill, JobStatus

# Caché en memoria para catálogos y filtros dinámicos de la búsqueda (5 minutos TTL) — HU-13
_FILTROS_CACHE: dict | None = None
_FILTROS_CACHE_TIME: float = 0.0
_CACHE_TTL_SECONDS: float = 300.0


class VacanteRepository:
    """Acceso a datos y persistencia para ofertas laborales y habilidades asociadas."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _query_base_con_relaciones(self):
        """Retorna la consulta base precargando todas las relaciones necesarias,
        minimizando los round-trips contra la Supabase remota (que domina el tiempo
        de respuesta por sobre el volumen de datos en listados chicos).

        company/category son muchos-a-uno: se cargan con joinedload (un solo JOIN,
        sin costo extra de round-trip). skills es uno-a-muchos y estas queries usan
        LIMIT/OFFSET para paginar: joinedload ahí corrompería la paginación (el
        LIMIT se aplicaría sobre las filas ya multiplicadas por el JOIN), así que
        se mantiene selectinload para esa relación.
        """
        return select(JobPosting).options(
            joinedload(JobPosting.company),
            joinedload(JobPosting.category),
            selectinload(JobPosting.skills).selectinload(JobSkill.skill),
        )

    def crear(self, vacante: JobPosting, skills: list[JobSkill] | None = None) -> JobPosting:
        """Persiste una nueva vacante y sus habilidades en la base de datos."""
        self.db.add(vacante)
        self.db.flush()

        if skills:
            for item in skills:
                item.job_posting_id = vacante.id
                self.db.add(item)
            self.db.flush()

        return self.obtener_por_id(vacante.id) or vacante

    def obtener_por_id(self, vacante_id: uuid.UUID) -> JobPosting | None:
        """Obtiene una vacante por su ID con todas sus relaciones cargadas."""
        stmt = self._query_base_con_relaciones().where(JobPosting.id == vacante_id)
        return self.db.execute(stmt).unique().scalar_one_or_none()

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
        items = list(self.db.execute(stmt).unique().scalars())

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

        if q:
            filtro_texto = or_(
                JobPosting.title.ilike(f"%{q.strip()}%"),
                JobPosting.description.ilike(f"%{q.strip()}%"),
            )
            stmt = stmt.where(filtro_texto)
            count_stmt = count_stmt.where(filtro_texto)

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
        items = list(self.db.execute(stmt).unique().scalars())

        return items, total

    def listar_por_estado(
        self,
        estado: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[JobPosting], int]:
        """Lista vacantes en un estado dado (usado por moderación para pendientes de revisión)."""
        stmt = self._query_base_con_relaciones().where(JobPosting.status == estado)
        count_stmt = select(func.count(JobPosting.id)).where(JobPosting.status == estado)

        total = self.db.scalar(count_stmt) or 0
        offset = (max(page, 1) - 1) * page_size

        stmt = stmt.order_by(JobPosting.created_at.asc()).offset(offset).limit(page_size)
        items = list(self.db.execute(stmt).unique().scalars())

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

        if nuevas_skills is not None:
            self.db.execute(delete(JobSkill).where(JobSkill.job_posting_id == vacante.id))
            for item in nuevas_skills:
                item.job_posting_id = vacante.id
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
        if nuevo_estado in (JobStatus.CLOSED.value, JobStatus.ARCHIVED.value) and vacante.closed_at is None:
            vacante.closed_at = datetime.now()
        vacante.updated_at = datetime.now()
        self.db.flush()
        return vacante

    def moderar(
        self,
        vacante: JobPosting,
        nuevo_estado: str,
        rejection_reason: str | None,
    ) -> JobPosting:
        """Aplica la decisión de moderación (aprobar/rechazar) sobre la vacante (HU-12)."""
        vacante.status = nuevo_estado
        vacante.rejection_reason = rejection_reason
        if nuevo_estado == JobStatus.PUBLISHED.value and vacante.published_at is None:
            vacante.published_at = datetime.now()
        vacante.updated_at = datetime.now()
        self.db.flush()
        return self.obtener_por_id(vacante.id) or vacante

    def eliminar(self, vacante: JobPosting) -> bool:
        """Elimina físicamente la vacante y sus habilidades dependientes en cascada."""
        self.db.delete(vacante)
        self.db.flush()
        return True

    # ─── Búsqueda avanzada con afinidad — HU-13 ─────────────────────────────

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
        """Busca vacantes publicadas aplicando filtros combinados y paginación por límite/desplazamiento."""
        stmt = select(JobPosting).where(JobPosting.status == JobStatus.PUBLISHED.value)

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
            stmt = stmt.where(or_(JobPosting.title.ilike(palabra), JobPosting.description.ilike(palabra)))

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
            stmt = stmt.where(or_(JobPosting.salary_max >= salario_min, JobPosting.salary_min >= salario_min))

        if salario_max is not None:
            stmt = stmt.where(or_(JobPosting.salary_min <= salario_max, JobPosting.salary_max <= salario_max))

        if carrera_id:
            stmt = stmt.join(
                JobEducationPreference, JobEducationPreference.job_posting_id == JobPosting.id
            ).where(JobEducationPreference.field_of_study_id == carrera_id)

        subq = stmt.subquery()
        total = self.db.scalar(select(func.count(distinct(subq.c.id)))) or 0

        if ordenar_por == "fecha":
            stmt = stmt.order_by(JobPosting.published_at.desc().nullslast(), JobPosting.created_at.desc())
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

    def obtener_por_id_con_afinidad(self, vacante_id: uuid.UUID) -> JobPosting | None:
        """Obtiene una vacante con las relaciones necesarias para calcular afinidad (skills + carreras)."""
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
        """Incrementa el contador de vistas de una vacante (usado por la búsqueda pública)."""
        self.db.execute(
            update(JobPosting).where(JobPosting.id == vacante_id).values(view_count=JobPosting.view_count + 1)
        )
        self.db.commit()

    def obtener_filtros_disponibles(self) -> dict:
        """Obtiene las opciones disponibles para los filtros de búsqueda, con caché en memoria."""
        global _FILTROS_CACHE, _FILTROS_CACHE_TIME

        ahora = time.time()
        if _FILTROS_CACHE is not None and (ahora - _FILTROS_CACHE_TIME) < _CACHE_TTL_SECONDS:
            return _FILTROS_CACHE

        publicadas = JobPosting.status == JobStatus.PUBLISHED.value

        ciudades = list(
            self.db.scalars(
                select(distinct(JobPosting.city)).where(publicadas, JobPosting.city.isnot(None)).order_by(JobPosting.city)
            )
        )
        modalidades = list(
            self.db.scalars(select(distinct(JobPosting.work_modality)).where(publicadas).order_by(JobPosting.work_modality))
        )
        jornadas = list(
            self.db.scalars(select(distinct(JobPosting.employment_type)).where(publicadas).order_by(JobPosting.employment_type))
        )
        seniorities = list(
            self.db.scalars(select(distinct(JobPosting.seniority_level)).where(publicadas).order_by(JobPosting.seniority_level))
        )
        categorias = list(self.db.scalars(select(JobCategory).where(JobCategory.is_active.is_(True)).order_by(JobCategory.name)))
        carreras = list(self.db.scalars(select(FieldOfStudy).order_by(FieldOfStudy.name)))

        salarios = self.db.execute(
            select(func.min(JobPosting.salary_min), func.max(JobPosting.salary_max)).where(
                publicadas, JobPosting.salary_visible.is_(True)
            )
        ).fetchone()

        resultado = {
            "ciudades": [c for c in ciudades if c],
            "modalidades": [m for m in modalidades if m],
            "jornadas": [j for j in jornadas if j],
            "niveles_experiencia": [s for s in seniorities if s],
            "categorias": [{"id": cat.id, "name": cat.name} for cat in categorias],
            "carreras": [{"id": car.id, "name": car.name, "category": car.category} for car in carreras],
            "salario_min_disponible": salarios[0] if salarios else None,
            "salario_max_disponible": salarios[1] if salarios else None,
        }

        _FILTROS_CACHE = resultado
        _FILTROS_CACHE_TIME = ahora
        return resultado
