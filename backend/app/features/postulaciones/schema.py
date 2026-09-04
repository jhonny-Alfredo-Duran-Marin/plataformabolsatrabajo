import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


ESTADOS_INFO: dict[str, dict[str, str]] = {
    "applied": {"label": "Postulado", "color": "blue", "step": "1"},
    "screening": {"label": "En revisión inicial", "color": "yellow", "step": "2"},
    "in_review": {"label": "En revisión", "color": "yellow", "step": "2"},
    "shortlisted": {"label": "Preseleccionado", "color": "purple", "step": "3"},
    "interview": {"label": "En entrevista", "color": "indigo", "step": "4"},
    "assessment": {"label": "En pruebas", "color": "cyan", "step": "5"},
    "offer": {"label": "Oferta recibida", "color": "emerald", "step": "6"},
    "hired": {"label": "Contratado", "color": "green", "step": "7"},
    "rejected": {"label": "No seleccionado", "color": "red", "step": "8"},
    "withdrawn": {"label": "Postulación retirada", "color": "gray", "step": "9"},
}

MODALIDADES_INFO: dict[str, str] = {
    "onsite": "Presencial",
    "hybrid": "Híbrido",
    "remote": "Remoto",
}

TIPOS_EMPLEO_INFO: dict[str, str] = {
    "permanent": "Tiempo Completo / Indefinido",
    "temporary": "Temporal",
    "contract": "Por Contrato",
    "internship": "Pasantía / Prácticas",
    "part_time": "Medio Tiempo",
    "freelance": "Freelance",
}


class HabilidadItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nombre: str
    importancia: str | None = None
    nivel_minimo: str | None = None


class PostulacionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    job_titulo: str
    empresa_id: uuid.UUID
    empresa_nombre: str
    empresa_ciudad: str | None = None
    modalidad: str
    modalidad_label: str
    tipo_empleo: str
    tipo_empleo_label: str
    salario_min: Decimal | None = None
    salario_max: Decimal | None = None
    currency: str | None = "BOB"
    salario_visible: bool = False
    estado: str
    estado_label: str
    estado_color: str
    etapa_actual_nombre: str | None = None
    fecha_postulacion: datetime
    fecha_ultimo_cambio: datetime
    cover_letter: str | None = None
    puede_retirar: bool = True


class HistorialEstadoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    desde_estado: str | None = None
    desde_estado_label: str | None = None
    hacia_estado: str
    hacia_estado_label: str
    hacia_estado_color: str
    motivo: str | None = None
    fecha: datetime


class EtapaHistorialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    etapa_nombre: str
    etapa_numero: int | None = None
    resultado: str | None = None
    resultado_label: str | None = None
    notas: str | None = None
    fecha_ingreso: datetime
    fecha_salida: datetime | None = None


class DetalleVacanteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    descripcion: str
    empresa_id: uuid.UUID
    empresa_nombre: str
    empresa_rubro: str | None = None
    empresa_tamano: str | None = None
    empresa_descripcion: str | None = None
    ciudad: str | None = None
    pais: str | None = None
    modalidad: str
    modalidad_label: str
    tipo_empleo: str
    tipo_empleo_label: str
    seniority: str | None = None
    anios_experiencia_min: int | None = None
    nivel_educativo_min: str | None = None
    salario_min: Decimal | None = None
    salario_max: Decimal | None = None
    currency: str | None = "BOB"
    salario_visible: bool = False
    posiciones_disponibles: int = 1
    habilidades: list[HabilidadItem] = []
    fecha_publicacion: datetime | None = None
    fecha_limite: datetime | None = None


class DetallePostulacionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    postulacion: PostulacionItemResponse
    vacante: DetalleVacanteResponse
    historial_estados: list[HistorialEstadoResponse] = []
    historial_etapas: list[EtapaHistorialResponse] = []


class ResumenPostulacionesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int
    activas: int
    en_revision: int
    entrevistas_ofertas: int
    contratados: int
    finalizadas: int
    postulaciones: list[PostulacionItemResponse]


class RetirarPostulacionRequest(BaseModel):
    motivo: str | None = None
