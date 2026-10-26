"""Módulo 5.1.9 — Registro de colocación (HU-29): contrataciones de egresados que registra la universidad."""

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.features.colocaciones.schema import (
    ColocacionCreateRequest,
    ColocacionDeleteRequest,
    ColocacionesResponse,
    ColocacionItem,
    ColocacionUpdateRequest,
    EgresadoOpcion,
    EmpresaOpcion,
)
from app.features.colocaciones.service import ColocacionService
from app.security.permisos import requiere_permiso
from app.security.tenant import AlcanceStaff

router = APIRouter(prefix="/colocaciones", tags=["colocaciones"])


@router.post("", response_model=ColocacionItem, status_code=status.HTTP_201_CREATED)
def registrar_colocacion(
    data: ColocacionCreateRequest,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.colocaciones.registrar")),
    db: Session = Depends(get_db),
):
    """CP01: registra a mano una contratación (un egresado puede tener varias)."""
    return ColocacionService(db).crear(data, alcance, get_client_ip(request))


@router.get("", response_model=ColocacionesResponse)
def listar_colocaciones(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    estado: Literal["suggested", "confirmed", "cancelled"] | None = Query(
        default=None, description="Sin estado se ven las sugeridas y las confirmadas; «cancelled» son las eliminadas."
    ),
    q: str | None = Query(default=None, max_length=100, description="Egresado, cargo o empresa"),
    desde: date | None = Query(default=None, description="Fecha de inicio desde"),
    hasta: date | None = Query(default=None, description="Fecha de inicio hasta"),
    alcance: AlcanceStaff = Depends(requiere_permiso("menu.colocaciones")),
    db: Session = Depends(get_db),
):
    """Las colocaciones de la universidad (todas, para el superadmin), con las sugeridas primero."""
    return ColocacionService(db).listar(alcance, page, page_size, estado, q, desde, hasta)


@router.get("/egresados", response_model=list[EgresadoOpcion])
def buscar_egresados(
    q: str | None = Query(default=None, max_length=100),
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.colocaciones.registrar")),
    db: Session = Depends(get_db),
):
    """Egresados de la universidad para elegir al registrar una colocación."""
    return ColocacionService(db).egresados(alcance, q)


@router.get("/empresas", response_model=list[EmpresaOpcion])
def buscar_empresas(
    q: str | None = Query(default=None, max_length=100),
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.colocaciones.registrar")),
    db: Session = Depends(get_db),
):
    """Empresas registradas para elegir al registrar una colocación."""
    return ColocacionService(db).empresas(q)


@router.put("/{colocacion_id}", response_model=ColocacionItem)
def editar_colocacion(
    colocacion_id: uuid.UUID,
    data: ColocacionUpdateRequest,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.colocaciones.registrar")),
    db: Session = Depends(get_db),
):
    """CP03: corrige los datos de una colocación; exige el motivo del cambio."""
    return ColocacionService(db).editar(colocacion_id, data, alcance, get_client_ip(request))


@router.post("/{colocacion_id}/confirmar", response_model=ColocacionItem)
def confirmar_colocacion(
    colocacion_id: uuid.UUID,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.colocaciones.registrar")),
    db: Session = Depends(get_db),
):
    """CP02: confirma la colocación que la plataforma sugirió al pasar una postulación a Contratado."""
    return ColocacionService(db).confirmar(colocacion_id, alcance, get_client_ip(request))


@router.delete("/{colocacion_id}", response_model=ColocacionItem)
def eliminar_colocacion(
    colocacion_id: uuid.UUID,
    data: ColocacionDeleteRequest,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.colocaciones.eliminar")),
    db: Session = Depends(get_db),
):
    """CP04: baja lógica con motivo. La fila se conserva pero deja de contar."""
    return ColocacionService(db).eliminar(colocacion_id, data, alcance, get_client_ip(request))
