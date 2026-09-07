import csv
import io
import uuid
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
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
    carrera_id: uuid.UUID | None = Query(None, description="Filtra candidatos por carrera (HU-16)"),
    habilidad_id: uuid.UUID | None = Query(None, description="Filtra candidatos por habilidad declarada (HU-16)"),
    ordenar_por: str = Query("fecha", description="'fecha' o 'afinidad' (HU-16)"),
    current_user: CurrentUser = Depends(_solo_empresa),
    db: Session = Depends(get_db),
) -> PipelineVacanteResponse:
    """HU-17: Obtener el tablero/pipeline de postulantes organizados por etapas para la vacante.

    HU-16: admite filtrar el pool por carrera/habilidad y ordenar por fecha o afinidad.
    """
    return SeleccionService(db).obtener_pipeline_vacante(
        current_user.id_usuario,
        id_vacante,
        carrera_id=carrera_id,
        habilidad_id=habilidad_id,
        ordenar_por=ordenar_por,
    )


@router.get("/vacantes/{id_vacante}/pipeline/exportar")
def exportar_pool_postulantes(
    id_vacante: uuid.UUID,
    carrera_id: uuid.UUID | None = Query(None),
    habilidad_id: uuid.UUID | None = Query(None),
    ordenar_por: str = Query("fecha"),
    current_user: CurrentUser = Depends(_solo_empresa),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """HU-16: Exporta el pool de postulantes de la vacante en formato CSV."""
    pipeline = SeleccionService(db).obtener_pipeline_vacante(
        current_user.id_usuario,
        id_vacante,
        carrera_id=carrera_id,
        habilidad_id=habilidad_id,
        ordenar_por=ordenar_por,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Nombre", "Titular profesional", "Carrera", "Email", "Teléfono", "Ciudad", "Afinidad (%)", "Estado", "Etapa", "Fecha de postulación"]
    )
    for c in pipeline.candidatos:
        writer.writerow(
            [
                c.candidato_nombre,
                c.candidato_titular or "",
                c.candidato_carrera or "",
                c.candidato_email or "",
                c.candidato_telefono or "",
                c.candidato_ciudad or "",
                c.candidato_afinidad if c.candidato_afinidad is not None else "",
                c.estado_label,
                c.etapa_actual_nombre or "",
                c.fecha_postulacion.strftime("%Y-%m-%d %H:%M"),
            ]
        )
    buffer.seek(0)

    nombre_archivo = f"postulantes_{pipeline.vacante.titulo.replace(' ', '_')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


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
