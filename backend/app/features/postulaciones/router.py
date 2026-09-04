import uuid
from datetime import date
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.features.postulaciones.schema import (
    DetallePostulacionResponse,
    PostulacionItemResponse,
    ResumenPostulacionesResponse,
    RetirarPostulacionRequest,
)
from app.features.postulaciones.service import PostulacionService
from app.security.dependencies import CurrentUser, require_roles

router = APIRouter(prefix="/postulaciones", tags=["postulaciones"])

_solo_egresado = require_roles("candidate")


@router.get("/mis-postulaciones", response_model=ResumenPostulacionesResponse)
def obtener_mis_postulaciones(
    estado: str | None = Query(None, description="Filtrar por estado (applied, screening, in_review, shortlisted, interview, assessment, offer, hired, rejected, withdrawn)"),
    fecha_desde: date | None = Query(None, description="Fecha de postulación inicial (YYYY-MM-DD)"),
    fecha_hasta: date | None = Query(None, description="Fecha de postulación final (YYYY-MM-DD)"),
    busqueda: str | None = Query(None, description="Búsqueda por título de vacante o empresa"),
    current_user: CurrentUser = Depends(_solo_egresado),
    db: Session = Depends(get_db),
) -> ResumenPostulacionesResponse:
    """HU-15: Consultar listado y resumen de todas las postulaciones del egresado autenticado."""
    return PostulacionService(db).obtener_mis_postulaciones(
        user_id=current_user.id_usuario,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        busqueda=busqueda,
    )


@router.get("/{id_postulacion}", response_model=DetallePostulacionResponse)
def obtener_detalle_postulacion(
    id_postulacion: uuid.UUID,
    current_user: CurrentUser = Depends(_solo_egresado),
    db: Session = Depends(get_db),
) -> DetallePostulacionResponse:
    """HU-15: Consultar detalle de la vacante, postulación y el historial completo de cambios de estado."""
    return PostulacionService(db).obtener_detalle_postulacion(
        user_id=current_user.id_usuario,
        application_id=id_postulacion,
    )


@router.post("/{id_postulacion}/retirar", response_model=PostulacionItemResponse)
def retirar_postulacion(
    id_postulacion: uuid.UUID,
    data: RetirarPostulacionRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_egresado),
    db: Session = Depends(get_db),
) -> PostulacionItemResponse:
    """HU-15: Permitir al egresado retirar su postulación voluntariamente si se encuentra activa."""
    ip = get_client_ip(request)
    return PostulacionService(db).retirar_postulacion(
        user_id=current_user.id_usuario,
        application_id=id_postulacion,
        motivo=data.motivo,
        ip=ip,
    )
