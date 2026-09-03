import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.vacantes.schema import (
    FiltrosDisponiblesResponse,
    VacanteDetalleResponse,
    VacantesPaginadasResponse,
)
from app.features.vacantes.service import VacanteService
from app.security.dependencies import CurrentUser, get_current_user_optional

router = APIRouter(prefix="/vacantes", tags=["vacantes"])


@router.get("", response_model=VacantesPaginadasResponse)
def buscar_vacantes(
    q: str | None = Query(None, description="Búsqueda por palabra clave en título o descripción"),
    carrera_id: uuid.UUID | None = Query(None, description="Filtro por carrera o campo de estudio"),
    categoria_id: uuid.UUID | None = Query(None, description="Filtro por categoría de empleo"),
    ciudad: str | None = Query(None, description="Filtro por ciudad"),
    modalidad: str | None = Query(None, description="Filtro por modalidad (on_site, remote, hybrid)"),
    jornada: str | None = Query(None, description="Filtro por jornada (full_time, part_time, internship, contractor)"),
    seniority: str | None = Query(None, description="Filtro por nivel de experiencia (junior, mid, senior, etc.)"),
    salario_min: Decimal | None = Query(None, description="Rango salarial mínimo"),
    salario_max: Decimal | None = Query(None, description="Rango salarial máximo"),
    ordenar_por: str = Query("fecha", description="Criterio de ordenamiento: 'fecha' o 'afinidad'"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad de resultados por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
    current_user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Busca y filtra vacantes laborales publicadas y vigentes con cálculo opcional de afinidad para egresados."""
    usuario_id = current_user.id_usuario if current_user else None
    return VacanteService(db).buscar_vacantes(
        q=q,
        carrera_id=carrera_id,
        categoria_id=categoria_id,
        ciudad=ciudad,
        modalidad=modalidad,
        jornada=jornada,
        seniority=seniority,
        salario_min=salario_min,
        salario_max=salario_max,
        ordenar_por=ordenar_por,
        limit=limit,
        offset=offset,
        usuario_id=usuario_id,
    )


@router.get("/filtros", response_model=FiltrosDisponiblesResponse)
def obtener_filtros_disponibles(db: Session = Depends(get_db)):
    """Retorna las opciones disponibles de filtrado (ciudades, modalidades, categorías, carreras, salarios)."""
    return VacanteService(db).obtener_filtros_disponibles()


@router.get("/{vacante_id}", response_model=VacanteDetalleResponse)
def obtener_detalle_vacante(
    vacante_id: uuid.UUID,
    current_user: CurrentUser | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Obtiene el detalle completo de una vacante e incrementa el contador de vistas."""
    usuario_id = current_user.id_usuario if current_user else None
    return VacanteService(db).obtener_detalle(vacante_id, usuario_id=usuario_id)
