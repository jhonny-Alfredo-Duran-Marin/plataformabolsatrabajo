"""Esquemas de datos para el Tablero de Indicadores (HU-31) y su Exportación (HU-32)."""

import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class HabilidadDemandaDTO(BaseModel):
    habilidad: str
    total_menciones: int
    porcentaje: float

    model_config = ConfigDict(from_attributes=True)


class TableroIndicadoresResponse(BaseModel):
    """Métricas consolidadas de inserción laboral para el administrador universitario (HU-31)."""

    institucion_id: uuid.UUID | None = None
    institucion_nombre: str | None = None
    carrera_id: uuid.UUID | None = None
    carrera_nombre: str | None = None
    periodo: str | None = None
    calculado_en: datetime

    # Indicadores Clave
    tasa_colocacion: float = Field(..., description="Porcentaje de egresados colocados (0-100)")
    tiempo_promedio_primer_empleo_meses: float | None = Field(
        ..., description="Meses promedio hasta el primer empleo (null si no hay datos para medirlo)"
    )
    pertinencia_carrera_porcentaje: float | None = Field(
        ..., description="Porcentaje de pertinencia con la carrera, 0-100 (null sin respuestas de encuesta)"
    )
    
    # Muestras y representatividad estadística (CP04)
    total_egresados_muestra: int
    total_colocados: int
    total_encuestas_respondidas: int
    muestra_suficiente: bool = Field(..., description="True si N >= 5, False si N < 5")
    advertencia_muestra: str | None = None

    # Distribuciones
    top_habilidades_demandadas: list[HabilidadDemandaDTO] = []
    colocaciones_por_modalidad: dict[str, int] = {}

    model_config = ConfigDict(from_attributes=True)


class ExportarIndicadoresRequest(BaseModel):
    """Parámetros para exportar el tablero de indicadores a PDF o Excel (HU-32)."""

    formato: Literal["pdf", "xlsx", "excel"] = Field(default="pdf", description="Formato de exportación deseado")
    carrera_id: uuid.UUID | None = Field(default=None, description="Filtrar por carrera específica")
    periodo: str | None = Field(default=None, description="Filtrar por período (ej. '2026', '2025-2')")

