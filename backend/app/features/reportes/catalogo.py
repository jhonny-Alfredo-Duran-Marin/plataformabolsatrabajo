"""Catálogo de los reportes personalizados (requisito general 5).

Cada fuente define las columnas y los filtros que el usuario puede elegir, siempre de una
lista cerrada (nunca SQL armado con lo que escribe el usuario), y desde dónde se consulta
según quién pide el reporte: el admin de una universidad ve solo lo suyo, el superadmin
todo y una empresa solo sus vacantes y sus postulantes.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import Select, String, case, cast, func, select
from sqlalchemy.orm import Session

from app.core.tenancy import INSTITUCION_POR_DEFECTO_ID, condicion_institucion
from app.features.vacantes.repository import empresa_vinculada_a
from app.models.candidato import CandidateEducation, CandidateProfile
from app.models.catalogo import JobCategory
from app.models.empresa import Company, Sector
from app.models.institucion import CompanyInstitution, Institution
from app.models.postulacion import Application
from app.models.usuario import AppUser
from app.models.vacante import JobPosting, JobSelectionStage

TipoColumna = Literal["texto", "numero", "fecha", "estado", "booleano"]
TipoFiltro = Literal["texto", "opciones", "fechas", "numeros"]


@dataclass
class Contexto:
    """Quién pide el reporte: define qué filas y columnas puede ver."""

    rol: Literal["staff", "empresa"]
    institution_id: uuid.UUID | None = None  # staff: None = superadmin de la plataforma
    company_id: uuid.UUID | None = None  # empresa

    @property
    def es_superadmin(self) -> bool:
        return self.rol == "staff" and self.institution_id is None


def _siempre(_: Contexto) -> bool:
    return True


def _solo_superadmin(ctx: Contexto) -> bool:
    return ctx.es_superadmin


def _solo_staff(ctx: Contexto) -> bool:
    return ctx.rol == "staff"


@dataclass(frozen=True)
class Columna:
    clave: str
    etiqueta: str
    tipo: TipoColumna
    expr: Callable[[Contexto], Any]
    opciones: dict[str, str] = field(default_factory=dict)  # valor guardado -> texto que se muestra
    por_defecto: bool = False
    visible: Callable[[Contexto], bool] = _siempre


@dataclass(frozen=True)
class Filtro:
    clave: str
    etiqueta: str
    tipo: TipoFiltro
    expr: Callable[[Contexto], Any]
    opciones: dict[str, str] = field(default_factory=dict)
    # Opciones que salen de la base (p. ej. sectores); se calculan al pedir el catálogo.
    opciones_de: Callable[[Session], dict[str, str]] | None = None
    visible: Callable[[Contexto], bool] = _siempre


@dataclass(frozen=True)
class Fuente:
    clave: str
    nombre: str
    descripcion: str
    roles: frozenset[str]
    columnas: tuple[Columna, ...]
    filtros: tuple[Filtro, ...]
    # FROM, JOIN y el WHERE del alcance (universidad o empresa); las columnas se eligen después.
    base: Callable[[Contexto], Select]
    orden: tuple[tuple[str, str], ...]


# ─── Textos de los estados ───────────────────────────────────────────────────

VERIFICACION = {"pending": "Pendiente", "in_review": "En revisión", "verified": "Verificado", "rejected": "Rechazado"}
BUSQUEDA = {
    "actively_looking": "Buscando activamente",
    "open_to_offers": "Abierto a ofertas",
    "not_looking": "No está buscando",
}
TAMANO = {"startup": "Startup", "small": "Pequeña", "medium": "Mediana", "large": "Grande", "corporation": "Corporación"}
CUENTA = {"active": "Activa", "suspended": "Suspendida"}
VINCULO = {"pending": "Pendiente", "approved": "Habilitada", "rejected": "Rechazada", "suspended": "Suspendida"}
ESTADO_VACANTE = {
    "draft": "Borrador",
    "pending_review": "En revisión",
    "published": "Publicada",
    "paused": "Pausada",
    "closed": "Cerrada",
    "rejected": "Rechazada",
    "archived": "Archivada",
}
MODALIDAD = {"onsite": "Presencial", "hybrid": "Híbrida", "remote": "Remota"}
NIVEL = {"internship": "Pasantía", "junior": "Junior", "mid": "Semi senior", "senior": "Senior", "lead": "Líder"}
CONTRATO = {
    "permanent": "Indefinido",
    "temporary": "Temporal",
    "contract": "Por contrato",
    "internship": "Pasantía",
    "part_time": "Medio tiempo",
    "freelance": "Freelance",
}
ESTADO_POSTULACION = {
    "applied": "Postulado",
    "screening": "En revisión",
    "in_review": "En análisis",
    "shortlisted": "Preseleccionado",
    "interview": "En entrevista",
    "assessment": "En pruebas",
    "offer": "Oferta",
    "hired": "Contratado",
    "rejected": "Descartado",
    "withdrawn": "Retirada",
}


def _sectores(db: Session) -> dict[str, str]:
    return {nombre: nombre for nombre in db.scalars(select(Sector.name).order_by(Sector.name))}


def _universidades(db: Session) -> dict[str, str]:
    filas = db.execute(
        select(Institution.id, Institution.name).where(Institution.is_tenant.is_(True)).order_by(Institution.name)
    )
    return {str(i): nombre for i, nombre in filas}


# ─── Egresados ───────────────────────────────────────────────────────────────

_NOMBRE_EGRESADO = func.concat_ws(" ", CandidateProfile.first_name, CandidateProfile.last_name)
_UNIVERSIDAD_EGRESADO = func.coalesce(CandidateProfile.institution_id, INSTITUCION_POR_DEFECTO_ID)
_CARRERA = (
    select(CandidateEducation.program_name)
    .where(CandidateEducation.candidate_id == CandidateProfile.id)
    .order_by(CandidateEducation.graduation_date.desc().nulls_last(), CandidateEducation.created_at.desc())
    .limit(1)
    .correlate(CandidateProfile)
    .scalar_subquery()
)
_POSTULACIONES_EGRESADO = (
    select(func.count(Application.id))
    .where(Application.candidate_id == CandidateProfile.id)
    .correlate(CandidateProfile)
    .scalar_subquery()
)


def _base_egresados(ctx: Contexto) -> Select:
    stmt = (
        select(CandidateProfile.id)
        .select_from(CandidateProfile)
        .join(AppUser, AppUser.id == CandidateProfile.user_id)
        .outerjoin(Institution, Institution.id == _UNIVERSIDAD_EGRESADO)
    )
    if ctx.institution_id is not None:
        stmt = stmt.where(condicion_institucion(CandidateProfile.institution_id, ctx.institution_id))
    return stmt


EGRESADOS = Fuente(
    clave="egresados",
    nombre="Egresados",
    descripcion="Egresados registrados, su validación, carrera y actividad en la plataforma.",
    roles=frozenset({"staff"}),
    columnas=(
        Columna("nombre", "Nombre", "texto", lambda c: _NOMBRE_EGRESADO, por_defecto=True),
        Columna("correo", "Correo", "texto", lambda c: AppUser.email, por_defecto=True),
        Columna("universidad", "Universidad", "texto", lambda c: Institution.name, visible=_solo_superadmin),
        Columna("carrera", "Carrera", "texto", lambda c: _CARRERA, por_defecto=True),
        Columna(
            "validacion", "Validación", "estado", lambda c: CandidateProfile.verification_status, VERIFICACION, True
        ),
        Columna("ciudad", "Ciudad", "texto", lambda c: CandidateProfile.city),
        Columna("telefono", "Teléfono", "texto", lambda c: CandidateProfile.phone),
        Columna("titular", "Titular profesional", "texto", lambda c: CandidateProfile.professional_headline),
        Columna("busqueda", "Búsqueda de empleo", "estado", lambda c: CandidateProfile.job_search_status, BUSQUEDA),
        Columna("postulaciones", "Postulaciones", "numero", lambda c: _POSTULACIONES_EGRESADO, por_defecto=True),
        Columna("registrado", "Registrado", "fecha", lambda c: CandidateProfile.created_at, por_defecto=True),
        Columna("verificado", "Verificado el", "fecha", lambda c: CandidateProfile.verified_at),
    ),
    filtros=(
        Filtro("nombre", "Nombre", "texto", lambda c: _NOMBRE_EGRESADO),
        Filtro("correo", "Correo", "texto", lambda c: AppUser.email),
        Filtro(
            "universidad",
            "Universidad",
            "opciones",
            lambda c: cast(_UNIVERSIDAD_EGRESADO, String),
            opciones_de=_universidades,
            visible=_solo_superadmin,
        ),
        Filtro("carrera", "Carrera", "texto", lambda c: _CARRERA),
        Filtro("validacion", "Validación", "opciones", lambda c: CandidateProfile.verification_status, VERIFICACION),
        Filtro("busqueda", "Búsqueda de empleo", "opciones", lambda c: CandidateProfile.job_search_status, BUSQUEDA),
        Filtro("ciudad", "Ciudad", "texto", lambda c: CandidateProfile.city),
        Filtro("registrado", "Registrado", "fechas", lambda c: CandidateProfile.created_at),
        Filtro("postulaciones", "Postulaciones", "numeros", lambda c: _POSTULACIONES_EGRESADO),
    ),
    base=_base_egresados,
    orden=(("registrado", "desc"),),
)


# ─── Empresas ────────────────────────────────────────────────────────────────


def _vinculo_en(ctx: Contexto):
    return (
        select(CompanyInstitution.status)
        .where(CompanyInstitution.company_id == Company.id, CompanyInstitution.institution_id == ctx.institution_id)
        .correlate(Company)
        .scalar_subquery()
    )


_UNIVERSIDADES_HABILITADAS = (
    select(func.count())
    .select_from(CompanyInstitution)
    .where(CompanyInstitution.company_id == Company.id, CompanyInstitution.status == "approved")
    .correlate(Company)
    .scalar_subquery()
)
_VACANTES_PUBLICADAS = (
    select(func.count(JobPosting.id))
    .where(JobPosting.company_id == Company.id, JobPosting.status == "published")
    .correlate(Company)
    .scalar_subquery()
)
_VACANTES_TOTALES = (
    select(func.count(JobPosting.id)).where(JobPosting.company_id == Company.id).correlate(Company).scalar_subquery()
)


def _base_empresas(ctx: Contexto) -> Select:
    stmt = select(Company.id).select_from(Company).outerjoin(Sector, Sector.id == Company.sector_id)
    if ctx.institution_id is not None:
        stmt = stmt.where(
            select(CompanyInstitution.company_id)
            .where(
                CompanyInstitution.company_id == Company.id,
                CompanyInstitution.institution_id == ctx.institution_id,
            )
            .exists()
        )
    return stmt


EMPRESAS = Fuente(
    clave="empresas",
    nombre="Empresas",
    descripcion="Empresas registradas, su verificación y su actividad publicando ofertas.",
    roles=frozenset({"staff"}),
    columnas=(
        Columna("razon_social", "Razón social", "texto", lambda c: Company.legal_name, por_defecto=True),
        Columna("nombre_comercial", "Nombre comercial", "texto", lambda c: Company.trade_name),
        Columna("nit", "NIT", "texto", lambda c: Company.tax_id, por_defecto=True),
        Columna("sector", "Sector", "texto", lambda c: Sector.name, por_defecto=True),
        Columna("tamano", "Tamaño", "estado", lambda c: Company.company_size, TAMANO),
        Columna("ciudad", "Ciudad", "texto", lambda c: Company.city),
        Columna("correo", "Correo de contacto", "texto", lambda c: Company.contact_email),
        Columna("telefono", "Teléfono", "texto", lambda c: Company.phone),
        Columna("verificacion", "Verificación", "estado", lambda c: Company.verification_status, VERIFICACION, True),
        Columna("cuenta", "Cuenta", "estado", lambda c: Company.account_status, CUENTA),
        Columna(
            "en_mi_universidad",
            "En mi universidad",
            "estado",
            _vinculo_en,
            VINCULO,
            True,
            visible=lambda c: c.institution_id is not None,
        ),
        Columna(
            "universidades",
            "Universidades habilitadas",
            "numero",
            lambda c: _UNIVERSIDADES_HABILITADAS,
            visible=_solo_superadmin,
            por_defecto=True,
        ),
        Columna("vacantes_publicadas", "Vacantes publicadas", "numero", lambda c: _VACANTES_PUBLICADAS, por_defecto=True),
        Columna("vacantes_totales", "Vacantes en total", "numero", lambda c: _VACANTES_TOTALES),
        Columna("registrada", "Registrada", "fecha", lambda c: Company.created_at, por_defecto=True),
    ),
    filtros=(
        Filtro("razon_social", "Razón social o nombre", "texto", lambda c: func.concat_ws(" ", Company.legal_name, Company.trade_name)),
        Filtro("sector", "Sector", "opciones", lambda c: Sector.name, opciones_de=_sectores),
        Filtro("verificacion", "Verificación", "opciones", lambda c: Company.verification_status, VERIFICACION),
        Filtro("cuenta", "Cuenta", "opciones", lambda c: Company.account_status, CUENTA),
        Filtro(
            "en_mi_universidad",
            "En mi universidad",
            "opciones",
            _vinculo_en,
            VINCULO,
            visible=lambda c: c.institution_id is not None,
        ),
        Filtro("tamano", "Tamaño", "opciones", lambda c: Company.company_size, TAMANO),
        Filtro("ciudad", "Ciudad", "texto", lambda c: Company.city),
        Filtro("registrada", "Registrada", "fechas", lambda c: Company.created_at),
        Filtro("vacantes_publicadas", "Vacantes publicadas", "numeros", lambda c: _VACANTES_PUBLICADAS),
    ),
    base=_base_empresas,
    orden=(("registrada", "desc"),),
)


# ─── Vacantes ────────────────────────────────────────────────────────────────

_NOMBRE_EMPRESA = func.coalesce(Company.trade_name, Company.legal_name)
_POSTULACIONES_VACANTE = (
    select(func.count(Application.id)).where(Application.job_id == JobPosting.id).correlate(JobPosting).scalar_subquery()
)
_CONTRATADOS_VACANTE = (
    select(func.count(Application.id))
    .where(Application.job_id == JobPosting.id, Application.current_status == "hired")
    .correlate(JobPosting)
    .scalar_subquery()
)


def _base_vacantes(ctx: Contexto) -> Select:
    stmt = (
        select(JobPosting.id)
        .select_from(JobPosting)
        .join(Company, Company.id == JobPosting.company_id)
        .outerjoin(JobCategory, JobCategory.id == JobPosting.category_id)
    )
    if ctx.rol == "empresa":
        return stmt.where(JobPosting.company_id == ctx.company_id)
    if ctx.institution_id is not None:
        stmt = stmt.where(empresa_vinculada_a(ctx.institution_id, ("approved", "pending")))
    return stmt


VACANTES = Fuente(
    clave="vacantes",
    nombre="Vacantes",
    descripcion="Ofertas laborales con su estado, condiciones y cuántos se postularon.",
    roles=frozenset({"staff", "empresa"}),
    columnas=(
        Columna("titulo", "Vacante", "texto", lambda c: JobPosting.title, por_defecto=True),
        Columna("empresa", "Empresa", "texto", lambda c: _NOMBRE_EMPRESA, por_defecto=True, visible=_solo_staff),
        Columna("categoria", "Categoría", "texto", lambda c: JobCategory.name),
        Columna("ciudad", "Ciudad", "texto", lambda c: JobPosting.city),
        Columna("modalidad", "Modalidad", "estado", lambda c: JobPosting.work_modality, MODALIDAD),
        Columna("nivel", "Nivel", "estado", lambda c: JobPosting.seniority_level, NIVEL),
        Columna("contrato", "Contrato", "estado", lambda c: JobPosting.employment_type, CONTRATO),
        Columna("estado", "Estado", "estado", lambda c: JobPosting.status, ESTADO_VACANTE, True),
        Columna("puestos", "Puestos", "numero", lambda c: JobPosting.positions_available),
        Columna("salario_min", "Salario mínimo", "numero", lambda c: JobPosting.salary_min),
        Columna("salario_max", "Salario máximo", "numero", lambda c: JobPosting.salary_max),
        Columna("publicada", "Publicada", "fecha", lambda c: JobPosting.published_at, por_defecto=True),
        Columna("fecha_limite", "Fecha límite", "fecha", lambda c: JobPosting.application_deadline),
        Columna("postulaciones", "Postulaciones", "numero", lambda c: _POSTULACIONES_VACANTE, por_defecto=True),
        Columna("contratados", "Contratados", "numero", lambda c: _CONTRATADOS_VACANTE),
        Columna("vistas", "Vistas", "numero", lambda c: JobPosting.view_count),
        Columna("creada", "Creada", "fecha", lambda c: JobPosting.created_at),
    ),
    filtros=(
        Filtro("titulo", "Vacante", "texto", lambda c: JobPosting.title),
        Filtro("empresa", "Empresa", "texto", lambda c: _NOMBRE_EMPRESA, visible=_solo_staff),
        Filtro("estado", "Estado", "opciones", lambda c: JobPosting.status, ESTADO_VACANTE),
        Filtro("modalidad", "Modalidad", "opciones", lambda c: JobPosting.work_modality, MODALIDAD),
        Filtro("nivel", "Nivel", "opciones", lambda c: JobPosting.seniority_level, NIVEL),
        Filtro("contrato", "Contrato", "opciones", lambda c: JobPosting.employment_type, CONTRATO),
        Filtro("ciudad", "Ciudad", "texto", lambda c: JobPosting.city),
        Filtro("publicada", "Publicada", "fechas", lambda c: JobPosting.published_at),
        Filtro("postulaciones", "Postulaciones", "numeros", lambda c: _POSTULACIONES_VACANTE),
    ),
    base=_base_vacantes,
    orden=(("publicada", "desc"),),
)


# ─── Postulaciones ───────────────────────────────────────────────────────────

# Una empresa ve el correo del postulante solo si el egresado lo hizo visible.
def _correo_postulante(ctx: Contexto):
    if ctx.rol == "staff":
        return AppUser.email
    return case((CandidateProfile.contact_visibility.is_(True), AppUser.email), else_="Oculto por el egresado")


def _base_postulaciones(ctx: Contexto) -> Select:
    stmt = (
        select(Application.id)
        .select_from(Application)
        .join(JobPosting, JobPosting.id == Application.job_id)
        .join(Company, Company.id == JobPosting.company_id)
        .join(CandidateProfile, CandidateProfile.id == Application.candidate_id)
        .join(AppUser, AppUser.id == CandidateProfile.user_id)
        .outerjoin(JobSelectionStage, JobSelectionStage.id == Application.current_stage_id)
        .outerjoin(Institution, Institution.id == _UNIVERSIDAD_EGRESADO)
    )
    if ctx.rol == "empresa":
        return stmt.where(JobPosting.company_id == ctx.company_id)
    if ctx.institution_id is not None:
        stmt = stmt.where(condicion_institucion(CandidateProfile.institution_id, ctx.institution_id))
    return stmt


POSTULACIONES = Fuente(
    clave="postulaciones",
    nombre="Postulaciones",
    descripcion="Quién se postuló a qué vacante y en qué etapa del proceso está.",
    roles=frozenset({"staff", "empresa"}),
    columnas=(
        Columna("egresado", "Egresado", "texto", lambda c: _NOMBRE_EGRESADO, por_defecto=True),
        Columna("correo", "Correo", "texto", _correo_postulante),
        Columna("carrera", "Carrera", "texto", lambda c: _CARRERA),
        Columna("universidad", "Universidad", "texto", lambda c: Institution.name, visible=_solo_superadmin),
        Columna("vacante", "Vacante", "texto", lambda c: JobPosting.title, por_defecto=True),
        Columna("empresa", "Empresa", "texto", lambda c: _NOMBRE_EMPRESA, por_defecto=True, visible=_solo_staff),
        Columna("estado", "Estado", "estado", lambda c: Application.current_status, ESTADO_POSTULACION, True),
        Columna("etapa", "Etapa", "texto", lambda c: JobSelectionStage.name, por_defecto=True),
        Columna("ciudad", "Ciudad del egresado", "texto", lambda c: CandidateProfile.city),
        Columna("postulado", "Fecha de postulación", "fecha", lambda c: Application.applied_at, por_defecto=True),
        Columna("actualizado", "Última actualización", "fecha", lambda c: Application.updated_at),
        Columna("retirada", "Retirada el", "fecha", lambda c: Application.withdrawn_at),
    ),
    filtros=(
        Filtro("egresado", "Egresado", "texto", lambda c: _NOMBRE_EGRESADO),
        Filtro("carrera", "Carrera", "texto", lambda c: _CARRERA),
        Filtro(
            "universidad",
            "Universidad",
            "opciones",
            lambda c: cast(_UNIVERSIDAD_EGRESADO, String),
            opciones_de=_universidades,
            visible=_solo_superadmin,
        ),
        Filtro("vacante", "Vacante", "texto", lambda c: JobPosting.title),
        Filtro("empresa", "Empresa", "texto", lambda c: _NOMBRE_EMPRESA, visible=_solo_staff),
        Filtro("estado", "Estado", "opciones", lambda c: Application.current_status, ESTADO_POSTULACION),
        Filtro("etapa", "Etapa", "texto", lambda c: JobSelectionStage.name),
        Filtro("postulado", "Fecha de postulación", "fechas", lambda c: Application.applied_at),
    ),
    base=_base_postulaciones,
    orden=(("postulado", "desc"),),
)


FUENTES: dict[str, Fuente] = {f.clave: f for f in (EGRESADOS, EMPRESAS, VACANTES, POSTULACIONES)}
