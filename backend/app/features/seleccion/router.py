import uuid
<<<<<<< HEAD
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
=======
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
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad

router = APIRouter(prefix="/seleccion", tags=["proceso-seleccion"])

_solo_empresa = require_roles("empresa", "platform_admin")

<<<<<<< HEAD
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
=======

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
>>>>>>> 8a7aaf477858b3da8e1335d385ccfa4cc3d228ad
