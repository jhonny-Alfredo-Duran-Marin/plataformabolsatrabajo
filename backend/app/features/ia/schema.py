import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.features.vacantes.schema import CriterioAfinidadResponse, VacanteResumenResponse


# --- MODELOS PARA HU-23 (Egresado -> Vacantes) ---
class VacanteRecomendadaResponse(BaseModel):
    vacante: VacanteResumenResponse
    afinidad: int
    criterios: list[CriterioAfinidadResponse]
    ya_postulado: bool = False


class RecomendacionesResponse(BaseModel):
    calculado_en: datetime
    total: int
    perfil_faltantes: list[str]
    items: list[VacanteRecomendadaResponse]


# --- MODELOS PARA HU-24 (Empresa -> Sugerencia de Candidatos por Afinidad) ---
class CriterioSugerenciaDTO(BaseModel):
    clave: str
    nombre: str
    peso: int
    cumplimiento: int
    estado: str
    detalle: str
    coincidencias: list[str] = []
    faltantes: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class CandidatoSugeridoDTO(BaseModel):
    candidate_id: uuid.UUID
    user_id: uuid.UUID
    application_id: uuid.UUID | None = None
    first_name: str
    last_name: str
    professional_headline: str | None = None
    carrera_principal: str | None = None
    city: str | None = None
    afinidad_porcentaje: int
    nivel_coincidencia: str
    razones_principales: list[str] = []
    criterios: list[CriterioSugerenciaDTO] = []
    current_status: str | None = None
    applied_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SugerenciasCandidatosResponse(BaseModel):
    vacante_id: uuid.UUID
    vacante_titulo: str
    calculado_en: datetime
    umbral_minimo: int
    total_postulantes: int
    total_coincidentes: int
    items: list[CandidatoSugeridoDTO]


# --- MODELOS PARA HU-28 (Chatbot de orientación) ---
class ChatbotConsultaRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=1000, description="Pregunta en lenguaje natural del usuario")
    session_id: uuid.UUID | None = Field(default=None, description="ID de la sesión activa del chatbot")


class EnlaceUtilChatbotDTO(BaseModel):
    texto: str
    ruta: str


class PostulacionResumenChatbotDTO(BaseModel):
    application_id: uuid.UUID
    job_id: uuid.UUID
    job_title: str
    company_name: str
    current_status: str
    status_label: str
    etapa_actual: str | None = None
    applied_at: datetime


class ChatbotMensajeDTO(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ChatbotRespuestaResponse(BaseModel):
    session_id: uuid.UUID
    mensaje_usuario: ChatbotMensajeDTO
    respuesta: ChatbotMensajeDTO
    intencion: str
    en_alcance: bool
    postulaciones: list[PostulacionResumenChatbotDTO] = []
    sugerencias: list[str] = []
    enlaces_utiles: list[EnlaceUtilChatbotDTO] = []


class ChatbotSesionResponse(BaseModel):
    session_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None = None
    saludo: str
    sugerencias: list[str] = []
    mensajes: list[ChatbotMensajeDTO] = []
