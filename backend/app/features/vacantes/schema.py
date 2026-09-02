import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.vacante import (
    EmploymentType,
    JobStatus,
    SeniorityLevel,
    SkillImportance,
    SkillProficiencyLevel,
    WorkModality,
)


# ─── Habilidades asociadas a la vacante ─────────────────────────────────────


class JobSkillItemRequest(BaseModel):
    """Habilidad requerida enviada en el formulario de vacante."""

    skill_id: uuid.UUID
    importance: SkillImportance | None = None
    min_proficiency: SkillProficiencyLevel | None = None
    weight: int | None = Field(default=None, ge=0, le=100)


class JobSkillItemResponse(BaseModel):
    """Detalle de una habilidad requerida para respuesta al cliente."""

    skill_id: uuid.UUID
    skill_name: str | None = None
    importance: str | None = None
    min_proficiency: str | None = None
    weight: int | None = None

    model_config = {"from_attributes": True}


# ─── Peticiones de Creación y Edición ────────────────────────────────────────


class VacanteCreateRequest(BaseModel):
    """Datos necesarios para publicar o crear en borrador una vacante."""

    title: str = Field(..., min_length=3, max_length=200, description="Título del puesto")
    description: str = Field(..., min_length=10, description="Descripción del puesto")
    responsibilities_json: list[str] | None = Field(default=None, description="Responsabilidades principales")
    requirements_json: list[str] | None = Field(default=None, description="Requisitos y perfil buscado")
    benefits_json: list[str] | None = Field(default=None, description="Beneficios ofrecidos")
    category_id: uuid.UUID | None = None

    seniority_level: SeniorityLevel
    employment_type: EmploymentType
    work_modality: WorkModality = WorkModality.ONSITE
    min_education_level: str | None = None
    min_years_experience: int | None = Field(default=0, ge=0)

    country_code: str = Field(default="BO", max_length=2)
    city: str = Field(..., max_length=100)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)

    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="BOB", max_length=3)
    salary_visible: bool = True

    positions_available: int = Field(default=1, ge=1)
    status: JobStatus = Field(
        default=JobStatus.DRAFT,
        description="Estado inicial (draft o published). Las empresas no verificadas siempre quedarán en draft; "
        "al pedir 'published' pasa a revisión institucional (pending_review), salvo que lo cree un administrador.",
    )
    application_deadline: datetime | None = None
    skills: list[JobSkillItemRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def validar_coherencia(self) -> "VacanteCreateRequest":
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("El salario mínimo no puede ser mayor al salario máximo.")

        tiene_lat = self.latitude is not None
        tiene_lon = self.longitude is not None
        if tiene_lat != tiene_lon:
            raise ValueError("Latitud y longitud deben enviarse juntas o ambas ser nulas.")

        return self


class VacanteUpdateRequest(BaseModel):
    """Datos actualizables de una vacante existente."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10)
    responsibilities_json: list[str] | None = None
    requirements_json: list[str] | None = None
    benefits_json: list[str] | None = None
    category_id: uuid.UUID | None = None

    seniority_level: SeniorityLevel | None = None
    employment_type: EmploymentType | None = None
    work_modality: WorkModality | None = None
    min_education_level: str | None = None
    min_years_experience: int | None = Field(default=None, ge=0)

    country_code: str | None = Field(default=None, max_length=2)
    city: str | None = Field(default=None, max_length=100)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)

    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=3)
    salary_visible: bool | None = None

    positions_available: int | None = Field(default=None, ge=1)
    status: JobStatus | None = None
    application_deadline: datetime | None = None
    skills: list[JobSkillItemRequest] | None = None

    @model_validator(mode="after")
    def validar_coherencia(self) -> "VacanteUpdateRequest":
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                raise ValueError("El salario mínimo no puede ser mayor al salario máximo.")

        tiene_lat = self.latitude is not None
        tiene_lon = self.longitude is not None
        if tiene_lat != tiene_lon:
            raise ValueError("Latitud y longitud deben enviarse juntas o ambas ser nulas.")

        return self


class VacanteCambioEstadoRequest(BaseModel):
    """Solicitud de cambio explícito de estado de la vacante."""

    status: JobStatus


class VacanteModeracionRequest(BaseModel):
    """Decisión de moderación institucional sobre una vacante pendiente de revisión (HU-12)."""

    aprobado: bool
    motivo_rechazo: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validar_motivo(self) -> "VacanteModeracionRequest":
        if not self.aprobado and not (self.motivo_rechazo and self.motivo_rechazo.strip()):
            raise ValueError("Debe indicar el motivo del rechazo.")
        return self


# ─── Respuestas hacia el Cliente ─────────────────────────────────────────────


class VacanteResponse(BaseModel):
    """Información completa de una vacante."""

    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str | None = None
    created_by: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    category_name: str | None = None

    title: str
    description: str
    responsibilities_json: list[str] | None = None
    requirements_json: list[str] | None = None
    benefits_json: list[str] | None = None

    seniority_level: str
    employment_type: str
    work_modality: str
    min_education_level: str | None = None
    min_years_experience: int | None = None

    country_code: str
    city: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None

    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    currency: str | None = None
    salary_visible: bool = False

    positions_available: int = 1
    status: str
    rejection_reason: str | None = None
    application_deadline: datetime | None = None
    published_at: datetime | None = None
    closed_at: datetime | None = None
    view_count: int = 0
    created_at: datetime
    updated_at: datetime

    skills: list[JobSkillItemResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class VacantePaginadaResponse(BaseModel):
    """Listado paginado de vacantes."""

    items: list[VacanteResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
