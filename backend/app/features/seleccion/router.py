import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.features.seleccion.schema import (
    AvanzarEtapaRequest,
    CandidatoPipelineItem,
    ConfigurarEtapasRequest,
    DescartarCandidatoRequest,
    EtapaResponse,
    NotaInternaRequest,
    NotaInternaResponse,
    PipelineVacanteResponse,
    VacanteResumenSeleccion,
)
from app.features.seleccion.service import SeleccionService
from app.security.dependencies import CurrentUser, require_roles

router = APIRouter(prefix="/seleccion", tags=["proceso-seleccion"])

_solo_empresa = require_roles("empresa", "platform_admin")


@router.get("/vacantes", response_model=list[VacanteResumenSeleccion])
def listar_vacantes_seleccion(
    current_user: CurrentUser = Depends(_solo_empresa),
    db: Session = Depends(get_db),
) -> list[VacanteResumenSeleccion]:
    """Listar vacantes de la empresa con métricas de candidatos en proceso de selección."""
    return SeleccionService(db).listar_vacantes(current_user.id_usuario)


@router.get("/vacantes/{id_vacante}/etapas", response_model=list[EtapaResponse])
def obtener_etapas_vacante(
    id_vacante: uuid.UUID,
    current_user: CurrentUser = Depends(_solo_empresa),
    db: Session = Depends(get_db),
) -> list[EtapaResponse]:
    """HU-17: Consultar las etapas configuradas del proceso de selección para una vacante."""
    return SeleccionService(db).obtener_etapas_vacante(current_user.id_usuario, id_vacante)


@router.put("/vacantes/{id_vacante}/etapas", response_model=list[EtapaResponse])
def configurar_etapas_vacante(
    id_vacante: uuid.UUID,
    data: ConfigurarEtapasRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_empresa),
    db: Session = Depends(get_db),
) -> list[EtapaResponse]:
    """HU-17: Configurar y reordenar las etapas del proceso de selección para una vacante."""
    ip = get_client_ip(request)
    return SeleccionService(db).configurar_etapas(
        user_id=current_user.id_usuario,
        job_id=id_vacante,
        data=data,
        ip=ip,
    )


@router.get("/vacantes/{id_vacante}/pipeline", response_model=PipelineVacanteResponse)
def obtener_pipeline_vacante(
    id_vacante: uuid.UUID,
    current_user: CurrentUser = Depends(_solo_empresa),
    db: Session = Depends(get_db),
) -> PipelineVacanteResponse:
    """HU-17: Obtener el tablero/pipeline de postulantes organizados por etapas para la vacante."""
    return SeleccionService(db).obtener_pipeline_vacante(current_user.id_usuario, id_vacante)


@router.post("/postulaciones/{id_postulacion}/avanzar", response_model=CandidatoPipelineItem)
def avanzar_etapa_candidato(
    id_postulacion: uuid.UUID,
    data: AvanzarEtapaRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_empresa),
    db: Session = Depends(get_db),
) -> CandidatoPipelineItem:
    """HU-17: Avanzar un candidato a una etapa específica del proceso de selección."""
    ip = get_client_ip(request)
    return SeleccionService(db).avanzar_etapa(
        user_id=current_user.id_usuario,
        application_id=id_postulacion,
        data=data,
        ip=ip,
    )


@router.post("/postulaciones/{id_postulacion}/descartar", response_model=CandidatoPipelineItem)
def descartar_candidato(
    id_postulacion: uuid.UUID,
    data: DescartarCandidatoRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_empresa),
    db: Session = Depends(get_db),
) -> CandidatoPipelineItem:
    """HU-17: Descartar a un candidato del proceso de selección (bloquea avances futuros)."""
    ip = get_client_ip(request)
    return SeleccionService(db).descartar_candidato(
        user_id=current_user.id_usuario,
        application_id=id_postulacion,
        data=data,
        ip=ip,
    )


@router.get("/postulaciones/{id_postulacion}/notas", response_model=list[NotaInternaResponse])
def listar_notas_internas(
    id_postulacion: uuid.UUID,
    current_user: CurrentUser = Depends(_solo_empresa),
    db: Session = Depends(get_db),
) -> list[NotaInternaResponse]:
    """HU-17: Consultar las observaciones internas registradas por el equipo de la empresa."""
    return SeleccionService(db).listar_notas_internas(current_user.id_usuario, id_postulacion)


@router.post("/postulaciones/{id_postulacion}/notas", response_model=NotaInternaResponse, status_code=201)
def agregar_nota_interna(
    id_postulacion: uuid.UUID,
    data: NotaInternaRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_empresa),
    db: Session = Depends(get_db),
) -> NotaInternaResponse:
    """HU-17: Registrar una nueva observación interna visible solo para el equipo de la empresa."""
    ip = get_client_ip(request)
    return SeleccionService(db).agregar_nota_interna(
        user_id=current_user.id_usuario,
        application_id=id_postulacion,
        data=data,
        ip=ip,
    )
