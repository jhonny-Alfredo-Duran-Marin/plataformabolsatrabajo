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
