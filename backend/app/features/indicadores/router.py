"""Endpoints para el Tablero de Indicadores de Inserción Laboral (HU-31)."""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.indicadores.schema import IndicadoresFiltrosOpciones, IndicadoresResponse
from app.features.indicadores.service import IndicadoresService
from app.security.permisos import requiere_permiso
from app.security.tenant import AlcanceStaff

router = APIRouter(prefix="/indicadores", tags=["indicadores"])


@router.get("/filtros", response_model=IndicadoresFiltrosOpciones)
def obtener_filtros(
    alcance: AlcanceStaff = Depends(requiere_permiso("menu.indicadores")),
    db: Session = Depends(get_db),
):
    """Devuelve las carreras y períodos disponibles para los selectores de filtro del tablero."""
    return IndicadoresService(db).obtener_filtros_disponibles(alcance)


@router.get("/tablero", response_model=IndicadoresResponse)
def consultar_tablero(
    carrera_id: uuid.UUID | None = Query(default=None, description="Filtrar indicadores por carrera específica"),
    periodo: str | None = Query(default=None, description="Filtrar por período (ej. '2026', '2025-I')"),
    alcance: AlcanceStaff = Depends(requiere_permiso("menu.indicadores")),
    db: Session = Depends(get_db),
):
    """CP01, CP02, CP03, CP04:

    Calcula y devuelve el tablero de indicadores de inserción laboral:
    - Tasa de colocación
    - Tiempo promedio al primer empleo
    - Pertinencia del empleo
    - Demanda de habilidades
    - Si total colocaciones < 5: retorna 'hay_suficientes_datos = False' con mensaje 'Sin datos suficientes'.
    - Informa fecha_actualizacion con timestamp exacto.
    """
    return IndicadoresService(db).calcular_tablero(
        alcance=alcance,
        carrera_id=carrera_id,
        periodo=periodo,
    )
