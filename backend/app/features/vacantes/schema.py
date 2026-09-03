import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class EmpresaEnVacanteResponse(BaseModel):
    id: uuid.UUID
    legal_name: str
    trade_name: str | None = None
    city: str | None = None
    sector_name: str | None = None
    website: str | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class HabilidadEnVacanteResponse(BaseModel):
    skill_id: uuid.UUID
    name: str
    importance: str = "required"
    min_proficiency: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CarreraEnVacanteResponse(BaseModel):
    field_of_study_id: uuid.UUID
    name: str
    education_level: str | None = None
    is_required: bool = True

    model_config = ConfigDict(from_attributes=True)


class VacanteResumenResponse(BaseModel):
    id: uuid.UUID
    company: EmpresaEnVacanteResponse
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    title: str
    description: str
    seniority_level: str
    employment_type: str
    work_modality: str
    country_code: str
    city: str
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    currency: str | None = "BOB"
    salary_visible: bool = True
    positions_available: int = 1
    status: str
    min_education_level: str | None = None
    min_years_experience: int | None = 0
    application_deadline: datetime | None = None
    published_at: datetime | None = None
    view_count: int = 0
    skills: list[HabilidadEnVacanteResponse] = []
    education_preferences: list[CarreraEnVacanteResponse] = []
    afinidad_porcentaje: int | None = None

    model_config = ConfigDict(from_attributes=True)


class VacanteDetalleResponse(VacanteResumenResponse):
    responsibilities: list[str] = []
    requirements: list[str] = []
    benefits: list[str] = []
    company_contact_email: str | None = None
    company_phone: str | None = None
    company_address: str | None = None


class CategoriaFiltroItem(BaseModel):
    id: uuid.UUID
    name: str


class CarreraFiltroItem(BaseModel):
    id: uuid.UUID
    name: str
    category: str | None = None


class FiltrosDisponiblesResponse(BaseModel):
    ciudades: list[str]
    modalidades: list[str]
    jornadas: list[str]
    niveles_experiencia: list[str]
    categorias: list[CategoriaFiltroItem]
    carreras: list[CarreraFiltroItem]
    salario_min_disponible: Decimal | None = None
    salario_max_disponible: Decimal | None = None


class VacantesPaginadasResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[VacanteResumenResponse]

