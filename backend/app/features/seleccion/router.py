import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.seleccion.schema import (
    CandidatoEnTableroDTO,
    ConfigurarEtapasRequest,
    DescartarCandidatoRequest,
    EtapaResponse,
    HistorialPostulacionResponse,
    MoverCandidatoRequest,
    NotaInternaCreateRequest,
    NotaInternaResponse,
    TableroSeleccionResponse,
)
from app.features.seleccion.service import SeleccionService
from app.security.dependencies import CurrentUser, get_current_user, get_current_user_optional

router = APIRouter(prefix="/seleccion", tags=["proceso-seleccion"])


@router.get("/vacantes/{vacante_id}/tablero", response_model=TableroSeleccionResponse)
def obtener_tablero_seleccion(
    vacante_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user_optional),
):
    """Obtiene el tablero Kanban de selección con columnas por etapa y candidatos postulados."""
    return SeleccionService(db).obtener_tablero(vacante_id)


@router.get("/vacantes/{vacante_id}/etapas", response_model=list[EtapaResponse])
def obtener_etapas_vacante(
    vacante_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user_optional),
):
    """Obtiene las etapas configuradas para una vacante."""
    return SeleccionService(db).obtener_etapas(vacante_id)


@router.put("/vacantes/{vacante_id}/etapas", response_model=list[EtapaResponse])
def configurar_etapas_vacante(
    vacante_id: uuid.UUID,
    req: ConfigurarEtapasRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Configura, agrega o reordena las etapas del proceso de selección para una vacante."""
    return SeleccionService(db).configurar_etapas(vacante_id, req)


@router.post("/postulaciones/{application_id}/mover", response_model=CandidatoEnTableroDTO)
def mover_candidato_etapa(
    application_id: uuid.UUID,
    req: MoverCandidatoRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Mueve a un candidato a una nueva etapa, registra la auditoría y le notifica."""
    return SeleccionService(db).mover_candidato(application_id, req, current_user.id_usuario)


@router.post("/postulaciones/{application_id}/descartar", response_model=CandidatoEnTableroDTO)
def descartar_candidato(
    application_id: uuid.UUID,
    req: DescartarCandidatoRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Descarta a un candidato en el proceso de selección y bloquea futuros avances."""
    return SeleccionService(db).descartar_candidato(application_id, req, current_user.id_usuario)


@router.get("/postulaciones/{application_id}/historial", response_model=HistorialPostulacionResponse)
def obtener_historial_postulacion(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Obtiene el historial de auditoría de avances y descartes de un postulante."""
    return SeleccionService(db).obtener_historial(application_id)


@router.get("/postulaciones/{application_id}/notas", response_model=list[NotaInternaResponse])
def obtener_notas_internas(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Obtiene las observaciones internas privadas de la empresa para un postulante."""
    return SeleccionService(db).obtener_notas(application_id)


@router.post(
    "/postulaciones/{application_id}/notas",
    response_model=NotaInternaResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_nota_interna(
    application_id: uuid.UUID,
    req: NotaInternaCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Registra una nueva observación interna privada para el postulante."""
    return SeleccionService(db).agregar_nota(application_id, req, current_user.id_usuario)
