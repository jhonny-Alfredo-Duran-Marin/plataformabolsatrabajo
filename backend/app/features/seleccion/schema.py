import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


<<<<<<< HEAD
class EtapaItemDTO(BaseModel):
=======
class EtapaItem(BaseModel):
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
    id: uuid.UUID | None = None
    stage_number: int = Field(..., ge=1)
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    is_terminal: bool = False

<<<<<<< HEAD
    model_config = ConfigDict(from_attributes=True)


class ConfigurarEtapasRequest(BaseModel):
    etapas: list[EtapaItemDTO] = Field(..., min_length=1)


class EtapaResponse(BaseModel):
=======

class EtapaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
    id: uuid.UUID
    job_posting_id: uuid.UUID
    stage_number: int
    name: str
    description: str | None = None
    is_terminal: bool = False
<<<<<<< HEAD
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
=======
    total_candidatos: int = 0


class ConfigurarEtapasRequest(BaseModel):
    etapas: list[EtapaItem] = Field(..., min_length=1)


class VacanteResumenSeleccion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    seniority: str | None = None
    modalidad: str
    modalidad_label: str
    tipo_empleo: str
    tipo_empleo_label: str
    total_postulantes: int = 0
    total_activos: int = 0
    total_descartados: int = 0
    total_contratados: int = 0


class CandidatoPipelineItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    postulacion_id: uuid.UUID
    candidato_id: uuid.UUID
    candidato_nombre: str
    candidato_titular: str | None = None
    candidato_carrera: str | None = None
    candidato_email: str | None = None
    candidato_telefono: str | None = None
    candidato_ciudad: str | None = None
    estado: str
    estado_label: str
    estado_color: str
    etapa_actual_id: uuid.UUID | None = None
    etapa_actual_nombre: str | None = None
    etapa_actual_numero: int | None = None
    fecha_postulacion: datetime
    fecha_ultimo_cambio: datetime
    total_notas: int = 0
    puede_avanzar: bool = True
    puede_descartar: bool = True


class PipelineVacanteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vacante: VacanteResumenSeleccion
    etapas: list[EtapaResponse]
    candidatos: list[CandidatoPipelineItem]


class AvanzarEtapaRequest(BaseModel):
    stage_id: uuid.UUID
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
    observacion: str | None = None


class DescartarCandidatoRequest(BaseModel):
    motivo: str | None = None


<<<<<<< HEAD
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
=======
class NotaInternaRequest(BaseModel):
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
    content: str = Field(..., min_length=1)


class NotaInternaResponse(BaseModel):
<<<<<<< HEAD
    id: uuid.UUID
    application_id: uuid.UUID
    author_id: uuid.UUID
    author_name: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

=======
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    postulacion_id: uuid.UUID
    autor_nombre: str
    autor_cargo: str | None = None
    content: str
    created_at: datetime
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
