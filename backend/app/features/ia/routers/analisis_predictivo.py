"""Módulo 5.1.14 — Análisis predictivo (HU-33): brecha de habilidades por carrera para el administrador."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.ia.schema_analisis_predictivo import BrechaFiltrosResponse, BrechaHabilidadesResponse
from app.features.ia.services.analisis_predictivo_service import LIMITE_PREDETERMINADO, AnalisisPredictivoService
from app.security.permisos import requiere_permiso
from app.security.tenant import AlcanceStaff

router = APIRouter(prefix="/ia/analisis-predictivo", tags=["analisis-predictivo"])


@router.get("/filtros", response_model=BrechaFiltrosResponse)
def filtros_brecha_habilidades(
    alcance: AlcanceStaff = Depends(requiere_permiso("menu.analisis_predictivo")),
    db: Session = Depends(get_db),
):
    """Carreras que piden las vacantes y períodos disponibles para los selectores del reporte."""
    return AnalisisPredictivoService(db).filtros_disponibles(alcance)


@router.get("/brecha-habilidades", response_model=BrechaHabilidadesResponse)
def brecha_habilidades(
    carrera_id: uuid.UUID = Query(description="Carrera a analizar"),
    periodo: str | None = Query(
        default=None,
        pattern=r"^\d{4}(-(0[1-9]|1[0-2]))?$",
        description="Período en que se publicaron las vacantes: AAAA o AAAA-MM. Sin período, todas.",
    ),
    limite: int = Query(default=LIMITE_PREDETERMINADO, ge=1, le=100, description="Máximo de habilidades a devolver"),
    alcance: AlcanceStaff = Depends(requiere_permiso("menu.analisis_predictivo")),
    db: Session = Depends(get_db),
):
    """HU-33: habilidades que piden las vacantes de la carrera frente a las que declaran sus egresados.

    Ordenadas de mayor a menor brecha. Con menos de 5 vacantes o 5 egresados responde 200 con
    `hay_suficientes_datos = false` y un mensaje. `resumen_ia` es opcional: si la IA está apagada o
    falla, vale null y el resto de la respuesta no cambia.
    """
    return AnalisisPredictivoService(db).brecha_habilidades_por_carrera(carrera_id, alcance, periodo, limite)
