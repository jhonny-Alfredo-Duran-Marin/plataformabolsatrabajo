"""Módulo 5.1.10 — Reportes institucionales: encuesta de situación laboral de los egresados (HU-30)."""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.features.encuestas.schema import (
    AvanceEncuesta,
    EncuestaCreada,
    EncuestaCreateRequest,
    EncuestaItem,
    EncuestasResponse,
    FormularioEncuesta,
    MiEncuestaItem,
    RespuestaCreada,
    RespuestaCreateRequest,
)
from app.features.encuestas.service import EncuestaService, avisar_encuesta_en_segundo_plano
from app.security.dependencies import CurrentUser, require_roles
from app.security.permisos import requiere_permiso
from app.security.tenant import AlcanceStaff

router = APIRouter(prefix="/encuestas", tags=["encuestas"])


# ─── Administrador universitario ─────────────────────────────────────────


@router.post("", response_model=EncuestaCreada, status_code=status.HTTP_201_CREATED)
def enviar_encuesta(
    data: EncuestaCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.encuestas.enviar")),
    db: Session = Depends(get_db),
):
    """HU-30: configura la encuesta de un período y la envía a los egresados de la universidad o de una carrera."""
    creada = EncuestaService(db).crear(data, alcance, get_client_ip(request))
    # El aviso a cada egresado (campanita y push) sale después de responder.
    background_tasks.add_task(avisar_encuesta_en_segundo_plano, creada.encuesta.id)
    return creada


@router.get("", response_model=EncuestasResponse)
def listar_encuestas(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    alcance: AlcanceStaff = Depends(requiere_permiso("menu.encuestas")),
    db: Session = Depends(get_db),
):
    """HU-30: las encuestas enviadas con su porcentaje de respuesta."""
    return EncuestaService(db).listar(alcance, page, page_size)


@router.get("/{encuesta_id}/avance", response_model=AvanceEncuesta)
def avance_de_la_encuesta(
    encuesta_id: uuid.UUID,
    alcance: AlcanceStaff = Depends(requiere_permiso("menu.encuestas")),
    db: Session = Depends(get_db),
):
    """HU-30: cuántos respondieron y cómo se reparte la situación laboral (solo conteos)."""
    return EncuestaService(db).avance(encuesta_id, alcance)


@router.post("/{encuesta_id}/cerrar", response_model=EncuestaItem)
def cerrar_encuesta(
    encuesta_id: uuid.UUID,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.encuestas.enviar")),
    db: Session = Depends(get_db),
):
    """Deja de recibir respuestas. Los egresados que ya respondieron la siguen viendo."""
    return EncuestaService(db).cerrar(encuesta_id, alcance, get_client_ip(request))


# ─── Egresado ────────────────────────────────────────────────────────────


@router.get("/mias", response_model=list[MiEncuestaItem])
def mis_encuestas(
    current_user: CurrentUser = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
):
    """HU-30: las encuestas que le llegaron al egresado, pendientes y respondidas."""
    return EncuestaService(db).mias(current_user)


@router.get("/{encuesta_id}/formulario", response_model=FormularioEncuesta)
def formulario_de_la_encuesta(
    encuesta_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
):
    return EncuestaService(db).formulario(encuesta_id, current_user)


@router.post("/{encuesta_id}/respuestas", response_model=RespuestaCreada, status_code=status.HTTP_201_CREATED)
def responder_encuesta(
    encuesta_id: uuid.UUID,
    data: RespuestaCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
):
    """HU-30: el egresado responde; una sola vez por encuesta (o sea, por período)."""
    return EncuestaService(db).responder(encuesta_id, data, current_user, get_client_ip(request))
