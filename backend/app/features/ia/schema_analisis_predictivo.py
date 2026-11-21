"""Esquemas del análisis predictivo (módulo 5.1.14, HU-33): brecha de habilidades por carrera."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class BrechaHabilidadItem(BaseModel):
    habilidad: str
    # Vacantes de la carrera (con habilidades) que la piden y su porcentaje sobre ese total.
    demanda_vacantes: int
    demanda_pct: float
    # Egresados verificados de la carrera que la declaran y su porcentaje sobre ese total.
    oferta_egresados: int
    oferta_pct: float
    # demanda_pct - oferta_pct, en puntos porcentuales. Positiva = faltan egresados con la habilidad.
    brecha: float


class BrechaHabilidadesResponse(BaseModel):
    carrera_id: uuid.UUID
    carrera_nombre: str
    # None = todas las vacantes sin importar cuándo se publicaron. Formatos: AAAA o AAAA-MM.
    periodo: str | None
    fecha_actualizacion: datetime
    hay_suficientes_datos: bool
    # Solo cuando faltan datos: explica qué falta y cuánto hay.
    mensaje: str | None
    minimo_requerido: int
    total_vacantes: int
    total_egresados: int
    # Fuera del cálculo: vacantes de la carrera sin habilidades cargadas y egresados sin habilidades declaradas.
    vacantes_sin_habilidades: int
    egresados_sin_habilidades: int
    total_habilidades: int
    habilidades: list[BrechaHabilidadItem]
    # Lectura en texto de la brecha. None si la IA está apagada, falló o no hay datos suficientes.
    resumen_ia: str | None = None


class CarreraOpcion(BaseModel):
    id: uuid.UUID
    nombre: str


class BrechaFiltrosResponse(BaseModel):
    carreras: list[CarreraOpcion]
    periodos: list[str]
