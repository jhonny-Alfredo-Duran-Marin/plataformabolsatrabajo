"""Rutas para búsqueda semántica de vacantes (HU-25).

Expone el endpoint oficial GET /api/search/semantic y alias convenientes.
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.ia.schema import BusquedaSemanticaResponse
from app.features.ia.services.semantic_search_service import SemanticSearchService
from app.security.dependencies import CurrentUser, get_current_user_optional

router = APIRouter(prefix="/search", tags=["busqueda-semantica"])


@router.get("/semantic", response_model=BusquedaSemanticaResponse)
def buscar_semantico(
    q: str = Query(..., min_length=1, max_length=500, description="Consulta en lenguaje natural"),
    ciudad: str | None = Query(default=None, max_length=100),
    modalidad: str | None = Query(default=None, description="remote, hybrid, onsite"),
    carrera_id: uuid.UUID | None = Query(default=None),
    salario_min: Decimal | None = Query(default=None, ge=0),
    seniority: str | None = Query(default=None, description="internship, junior, mid, senior, lead"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """HU-25: Búsqueda Semántica de Vacantes.

    Permite a egresados y visitantes buscar vacantes laborales utilizando lenguaje natural.
    El sistema interpreta la intención, evalúa afinidad semántica (0-100), justifica el match
    y combina con filtros estructurados.
    """
    return SemanticSearchService(db).buscar(
        q=q,
        ciudad=ciudad,
        modalidad=modalidad,
        carrera_id=carrera_id,
        salario_min=salario_min,
        seniority=seniority,
        page=page,
        page_size=page_size,
    )

