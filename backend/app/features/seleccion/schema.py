import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class EtapaItemDTO(BaseModel):
    id: uuid.UUID | None = None
    stage_number: int = Field(..., ge=1)
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    is_terminal: bool = False

    model_config = ConfigDict(from_attributes=True)


class ConfigurarEtapasRequest(BaseModel):
    etapas: list[EtapaItemDTO] = Field(..., min_length=1)


class EtapaResponse(BaseModel):
    id: uuid.UUID
    job_posting_id: uuid.UUID
    stage_number: int
    name: str
    description: str | None = None
    is_terminal: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidatoEnTableroDTO(BaseModel):
    application_id: uuid.UUID
    candidate_id: uuid.UUID
    user_id: uuid.UUID | None = None
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    professional_headline: str | None = None
    current_stage_id: uuid.UUID | None = None
    current_status: str
    applied_at: datetime
    notas_count: int = 0
    cover_letter: str | None = None
    afinidad_porcentaje: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ColumnaEtapaTableroDTO(BaseModel):
    stage: EtapaResponse
    candidatos: list[CandidatoEnTableroDTO] = []


class TableroSeleccionResponse(BaseModel):
    job_posting_id: uuid.UUID
    job_title: str
    company_id: uuid.UUID
    company_name: str
    total_candidatos: int
    columnas: list[ColumnaEtapaTableroDTO]
    candidatos_descartados: list[CandidatoEnTableroDTO] = []


class MoverCandidatoRequest(BaseModel):
    nueva_etapa_id: uuid.UUID
    observacion: str | None = None


class DescartarCandidatoRequest(BaseModel):
    motivo: str | None = None


class HistorialEtapaItemResponse(BaseModel):
    id: uuid.UUID
    stage_id: uuid.UUID
    stage_name: str
    entered_at: datetime
    left_at: datetime | None = None
    changed_by_id: uuid.UUID | None = None
    changed_by_name: str | None = None
    result: str | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class HistorialPostulacionResponse(BaseModel):
    application_id: uuid.UUID
    current_status: str
    historial: list[HistorialEtapaItemResponse]


class NotaInternaCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)


class NotaInternaResponse(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

