"""Rutas para el Tablero de Indicadores (HU-31) y Exportación a PDF/Excel (HU-32).

Expone endpoints bajo /indicators y /reportes/indicadores.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.features.reportes.indicadores_schema import (
    ExportarIndicadoresRequest,
    TableroIndicadoresResponse,
)
from app.features.reportes.indicadores_service import IndicadoresService
from app.models.usuario import AppUser
from app.security.dependencies import CurrentUser, require_roles
from app.security.tenant import alcance_staff

router = APIRouter(prefix="/indicators", tags=["indicadores"])
indicadores_reportes_router = APIRouter(prefix="/reportes/indicadores", tags=["indicadores"])

_solo_staff = require_roles("platform_admin", "moderator")


@router.get("", response_model=TableroIndicadoresResponse)
def obtener_indicadores(
    carrera_id: uuid.UUID | None = Query(default=None, description="Filtrar métricas por carrera"),
    periodo: str | None = Query(default=None, description="Filtrar por período (ej. '2026', '2025-2')"),
    current_user: CurrentUser = Depends(_solo_staff),
    db: Session = Depends(get_db),
):
    """HU-31: Retorna el consolidado de indicadores de inserción laboral para el administrador."""
    inst_id = alcance_staff(db, current_user)
    return IndicadoresService(db).calcular_tablero(
        institucion_id=inst_id,
        carrera_id=carrera_id,
        periodo=periodo,
    )


@indicadores_reportes_router.get("", response_model=TableroIndicadoresResponse)
def obtener_indicadores_alias(
    carrera_id: uuid.UUID | None = Query(default=None),
    periodo: str | None = Query(default=None),
    current_user: CurrentUser = Depends(_solo_staff),
    db: Session = Depends(get_db),
):
    return obtener_indicadores(carrera_id, periodo, current_user, db)


@router.get("/export")
def exportar_indicadores_get(
    request: Request,
    format: Literal["pdf", "xlsx", "excel"] = Query(default="pdf", description="Formato: pdf o xlsx"),
    carrera_id: uuid.UUID | None = Query(default=None),
    periodo: str | None = Query(default=None),
    current_user: CurrentUser = Depends(_solo_staff),
    db: Session = Depends(get_db),
):
    """HU-32: Exporta el tablero de indicadores a PDF o Excel vía GET."""
    inst_id = alcance_staff(db, current_user)
    usuario = db.get(AppUser, current_user.id_usuario)
    correo = usuario.email if usuario else None

    archivo = IndicadoresService(db).exportar(
        institucion_id=inst_id,
        carrera_id=carrera_id,
        periodo=periodo,
        formato=format,
        usuario_id=current_user.id_usuario,
        correo=correo,
        ip_address=get_client_ip(request),
    )

    return Response(
        content=archivo.contenido,
        media_type=archivo.tipo,
        headers={
            "Content-Disposition": f'attachment; filename="{archivo.nombre}"',
            "X-Total-Registros": str(archivo.total),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Total-Registros",
        },
    )


@indicadores_reportes_router.get("/export")
def exportar_indicadores_get_alias(
    request: Request,
    format: Literal["pdf", "xlsx", "excel"] = Query(default="pdf"),
    carrera_id: uuid.UUID | None = Query(default=None),
    periodo: str | None = Query(default=None),
    current_user: CurrentUser = Depends(_solo_staff),
    db: Session = Depends(get_db),
):
    return exportar_indicadores_get(request, format, carrera_id, periodo, current_user, db)


@router.post("/export")
def exportar_indicadores_post(
    payload: ExportarIndicadoresRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_staff),
    db: Session = Depends(get_db),
):
    """HU-32: Exporta el tablero de indicadores a PDF o Excel vía POST."""
    inst_id = alcance_staff(db, current_user)
    usuario = db.get(AppUser, current_user.id_usuario)
    correo = usuario.email if usuario else None

    archivo = IndicadoresService(db).exportar(
        institucion_id=inst_id,
        carrera_id=payload.carrera_id,
        periodo=payload.periodo,
        formato=payload.formato,
        usuario_id=current_user.id_usuario,
        correo=correo,
        ip_address=get_client_ip(request),
    )

    return Response(
        content=archivo.contenido,
        media_type=archivo.tipo,
        headers={
            "Content-Disposition": f'attachment; filename="{archivo.nombre}"',
            "X-Total-Registros": str(archivo.total),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Total-Registros",
        },
    )


@indicadores_reportes_router.post("/export")
def exportar_indicadores_post_alias(
    payload: ExportarIndicadoresRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_staff),
    db: Session = Depends(get_db),
):
    return exportar_indicadores_post(payload, request, current_user, db)

