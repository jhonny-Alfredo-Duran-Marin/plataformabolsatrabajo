"""Esquemas Pydantic para el Tablero de Indicadores de Inserción Laboral (HU-31)."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class HabilidadDemandaItem(BaseModel):
    nombre: str
    total: int
    porcentaje: float


class IndicadoresFiltrosOpciones(BaseModel):
    carreras: list[dict]
    periodos: list[str]


class IndicadoresResponse(BaseModel):
    # Metadatos del cálculo
    fecha_actualizacion: datetime = Field(
        description="Fecha y hora exacta en la que se calcularon o refrescaron los indicadores mostrados"
    )
    carrera_id: uuid.UUID | None = None
    carrera_nombre: str | None = None
    periodo: str | None = None

    # Regla de suficientes datos (menos de 5 colocaciones = False)
    hay_suficientes_datos: bool = Field(
        description="True si hay al menos 5 colocaciones para el filtro dado. False si hay menos de 5."
    )
    mensaje_insuficiente: str | None = Field(
        default=None,
        description="«Sin datos suficientes» cuando hay menos de 5 colocaciones registradas."
    )

    # Volúmenes
    total_egresados: int = 0
    total_colocaciones: int = 0
    total_encuestas_respondidas: int = 0

    # Indicadores principales (solo representativos si hay_suficientes_datos es True)
    tasa_colocacion: float | None = Field(
        default=None,
        description="Porcentaje de egresados de la carrera/período con colocación confirmada."
    )
    tiempo_promedio_primer_empleo_meses: float | None = Field(
        default=None,
        description="Meses promedio transcurridos entre la fecha de graduación y el inicio laboral."
    )
    pertinencia_empleo_porcentaje: float | None = Field(
        default=None,
        description="Porcentaje de egresados cuyo empleo tiene alta relación con su carrera según colocación y encuestas."
    )

    # Demanda de habilidades más frecuentes
    habilidades_demandadas: list[HabilidadDemandaItem] = Field(
        default_factory=list,
        description="Ranking de habilidades técnicas y blandas más demandadas o registradas en colocaciones."
    )
