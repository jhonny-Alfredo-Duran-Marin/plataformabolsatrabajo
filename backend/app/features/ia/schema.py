import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.features.vacantes.schema import CriterioAfinidadResponse, VacanteResumenResponse


# --- MODELOS PARA HU-26 (Asistente Generativo de Resumen Profesional) ---
class GenerarResumenRequest(BaseModel):
    variante: int = Field(default=1, ge=1, le=5, description="Índice de la variante de redacción deseada (para regenerar versiones alternativas)")
    enfoque: str | None = Field(default="general", description="Enfoque de redacción: general, tecnico, ejecutivo")


class GenerarResumenResponse(BaseModel):
    borrador: str
    generado_por_ia: bool = True
    advertencia: str = "Borrador generado por IA. Requiere revisión del egresado antes de guardarlo en el perfil."
    variante: int
    total_variantes: int = 3
    datos_utilizados: dict[str, Any] = {}


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


# --- MODELOS PARA HU-27 (Redacción Asistida de Vacante con IA) ---
class GenerarBorradorVacanteRequest(BaseModel):
    indicacion: str = Field(..., min_length=3, max_length=1000, description="Indicación breve sobre la vacante (ej. 'Desarrollador backend junior, remoto, python')")
    cargo: str | None = Field(default=None, description="Cargo sugerido u opcional")
    modalidad: str | None = Field(default=None, description="Modalidad de trabajo deseada: remote, hybrid, onsite")
    requisitos_clave: str | None = Field(default=None, description="Requisitos o habilidades clave")
    variante: int = Field(default=1, ge=1, le=5, description="Variante para generar redacciones alternativas")


class GenerarBorradorVacanteResponse(BaseModel):
    titulo: str
    descripcion: str
    requisitos: list[str]
    beneficios: list[str]
    modalidad: str
    seniority: str
    generado_por_ia: bool = True
    marca_auditoria: str = "Asistida por IA"
    indicacion_original: str
    fecha: datetime
    advertencia: str = "Borrador generado por IA. La empresa debe revisar y editar las secciones antes de enviar a moderación."


# --- MODELOS PARA HU-25 (Búsqueda Semántica de Vacantes) ---
class VacanteSemanticaItemDTO(BaseModel):
    id: uuid.UUID
    title: str
    company_name: str
    city: str
    work_modality: str
    seniority_level: str
    employment_type: str
    salary_min: Any | None = None
    salary_max: Any | None = None
    currency: str | None = "BOB"
    description: str
    score_relevancia: int = Field(..., ge=0, le=100, description="Puntaje de relevancia semántica (0-100)")
    razon_coincidencia: str = Field(..., description="Explicación del criterio de coincidencia semántica")
    published_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BusquedaSemanticaResponse(BaseModel):
    total: int
    consulta_original: str
    intencion_interpretada: dict[str, Any] = {}
    ia_disponible: bool = True
    sugerencia: str | None = None
    items: list[VacanteSemanticaItemDTO] = []
