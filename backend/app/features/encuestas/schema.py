import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class EncuestaCreateRequest(BaseModel):
    titulo: str = Field(min_length=3, max_length=250)
    descripcion: str | None = Field(default=None, max_length=1000)
    # Etiqueta del período que se mide ("2026-2", "Gestión 2026"): se responde una encuesta por período.
    periodo: str = Field(min_length=1, max_length=40)
    # Sin carrera, la encuesta va a todos los egresados de la universidad.
    carrera_id: uuid.UUID | None = None
    vence_el: date | None = None


class EncuestaItem(BaseModel):
    id: uuid.UUID
    titulo: str
    descripcion: str | None
    periodo: str
    alcance: Literal["todas", "universidad", "carrera"]
    carrera: str | None
    enviada_el: datetime
    vence_el: datetime | None
    activa: bool
    abierta: bool
    destinatarios: int
    respondieron: int
    porcentaje: float


class EncuestasResponse(BaseModel):
    items: list[EncuestaItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class EncuestaCreada(BaseModel):
    encuesta: EncuestaItem
    mensaje: str


class SituacionLaboralCantidad(BaseModel):
    codigo: str
    etiqueta: str
    cantidad: int


class AvanceEncuesta(BaseModel):
    encuesta: EncuestaItem
    pendientes: int
    # Solo conteos agregados: el administrador no ve qué respondió cada egresado.
    situacion_laboral: list[SituacionLaboralCantidad]


class MiEncuestaItem(BaseModel):
    id: uuid.UUID
    titulo: str
    descripcion: str | None
    periodo: str
    vence_el: datetime | None
    respondida: bool
    respondida_el: datetime | None


class OpcionEncuesta(BaseModel):
    id: uuid.UUID
    codigo: str | None
    texto: str


class PreguntaEncuesta(BaseModel):
    id: uuid.UUID
    codigo: str | None
    texto: str
    tipo: Literal["single_choice", "text", "number", "scale"]
    obligatoria: bool
    opciones: list[OpcionEncuesta]


class FormularioEncuesta(BaseModel):
    id: uuid.UUID
    titulo: str
    descripcion: str | None
    periodo: str
    vence_el: datetime | None
    preguntas: list[PreguntaEncuesta]


class RespuestaPregunta(BaseModel):
    pregunta_id: uuid.UUID
    opcion_id: uuid.UUID | None = None
    texto: str | None = Field(default=None, max_length=500)
    numero: float | None = None


class RespuestaCreateRequest(BaseModel):
    respuestas: list[RespuestaPregunta] = Field(max_length=20)


class RespuestaCreada(BaseModel):
    mensaje: str
    respondida_el: datetime
