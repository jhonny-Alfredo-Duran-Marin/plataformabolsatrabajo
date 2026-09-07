import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.features.perfil.schema import PerfilEgresadoResponse, ValidacionEgresadoDecisionRequest
from app.features.empresa.schema import (
    ConfiguracionEmpresaRequest,
    DecisionEmpresaRequest,
    EmpresaResponse,
    SuspensionEmpresaRequest,
)
from app.security.dependencies import CurrentUser, require_roles
from app.features.bitacora.service import BitacoraService
from app.features.perfil.service import EgresadoService
from app.features.empresa.service import EmpresaService
from app.features.vacantes.schema import VacanteModeracionRequest, VacantePaginadaResponse, VacanteResponse
from app.features.vacantes.service import VacanteService

router = APIRouter(prefix="/validacion", tags=["validacion-institucional"])

_solo_admin = require_roles("platform_admin", "moderator")


@router.get("/egresados/pendientes", response_model=list[PerfilEgresadoResponse])
def listar_egresados_pendientes(current_user: CurrentUser = Depends(_solo_admin), db: Session = Depends(get_db)):
    return EgresadoService(db).listar_pendientes_validacion()


@router.post("/egresados/{perfil_id}/decision", response_model=PerfilEgresadoResponse)
def decidir_egresado(
    perfil_id: uuid.UUID,
    data: ValidacionEgresadoDecisionRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_admin),
    db: Session = Depends(get_db),
):
    perfil = EgresadoService(db).validar(perfil_id, data.aprobado, data.motivo_rechazo)
    BitacoraService(db).registrar(
        modulo="validacion_institucional",
        accion="decidir_egresado",
        usuario_id=current_user.id_usuario,
        ip=get_client_ip(request),
        detalles=f"perfil_id={perfil_id} aprobado={data.aprobado}",
    )
    db.commit()
    return perfil


@router.get("/empresas/pendientes", response_model=list[EmpresaResponse])
def listar_empresas_pendientes(current_user: CurrentUser = Depends(_solo_admin), db: Session = Depends(get_db)):
    return EmpresaService(db).listar_pendientes()


@router.get("/empresas", response_model=list[EmpresaResponse])
def listar_todas_las_empresas(
    incluir_inactivas: bool = Query(default=False),
    current_user: CurrentUser = Depends(_solo_admin),
    db: Session = Depends(get_db),
):
    return EmpresaService(db).listar_todas(incluir_inactivas=incluir_inactivas)


@router.post("/empresas/{empresa_id}/decision", response_model=EmpresaResponse)
def decidir_empresa(
    empresa_id: uuid.UUID,
    data: DecisionEmpresaRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_admin),
    db: Session = Depends(get_db),
):
    empresa = EmpresaService(db).decidir(empresa_id, data.aprobado, data.motivo_rechazo)
    BitacoraService(db).registrar(
        modulo="validacion_institucional",
        accion="decidir_empresa",
        usuario_id=current_user.id_usuario,
        ip=get_client_ip(request),
        detalles=f"empresa_id={empresa_id} aprobado={data.aprobado}",
    )
    db.commit()
    return empresa


@router.post("/empresas/{empresa_id}/suspender", response_model=EmpresaResponse)
def suspender_empresa(
    empresa_id: uuid.UUID,
    data: SuspensionEmpresaRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_admin),
    db: Session = Depends(get_db),
):
    empresa = EmpresaService(db).suspender(empresa_id, data.motivo)
    BitacoraService(db).registrar(
        modulo="validacion_institucional",
        accion="suspender_empresa",
        usuario_id=current_user.id_usuario,
        ip=get_client_ip(request),
        detalles=f"empresa_id={empresa_id}",
    )
    db.commit()
    return empresa


@router.patch("/empresas/{empresa_id}/configuracion", response_model=EmpresaResponse)
def configurar_empresa(
    empresa_id: uuid.UUID,
    data: ConfiguracionEmpresaRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_admin),
    db: Session = Depends(get_db),
):
    empresa = EmpresaService(db).actualizar_configuracion(
        empresa_id,
        notificaciones_activas=data.notificaciones_activas,
        postulaciones_activas=data.postulaciones_activas,
    )
    BitacoraService(db).registrar(
        modulo="validacion_institucional",
        accion="configurar_empresa",
        usuario_id=current_user.id_usuario,
        ip=get_client_ip(request),
        detalles=f"empresa_id={empresa_id} notificaciones={data.notificaciones_activas} postulaciones={data.postulaciones_activas}",
    )
    db.commit()
    return empresa


@router.delete("/empresas/{empresa_id}", response_model=EmpresaResponse)
def eliminar_empresa_logico(
    empresa_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(_solo_admin),
    db: Session = Depends(get_db),
):
    empresa = EmpresaService(db).eliminar_logico(empresa_id)
    BitacoraService(db).registrar(
        modulo="validacion_institucional",
        accion="eliminar_empresa_logico",
        usuario_id=current_user.id_usuario,
        ip=get_client_ip(request),
        detalles=f"empresa_id={empresa_id}",
    )
    db.commit()
    return empresa


@router.post("/empresas/{empresa_id}/restaurar", response_model=EmpresaResponse)
def restaurar_empresa(
    empresa_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(_solo_admin),
    db: Session = Depends(get_db),
):
    empresa = EmpresaService(db).restaurar(empresa_id)
    BitacoraService(db).registrar(
        modulo="validacion_institucional",
        accion="restaurar_empresa",
        usuario_id=current_user.id_usuario,
        ip=get_client_ip(request),
        detalles=f"empresa_id={empresa_id}",
    )
    db.commit()
    return empresa


# ─── Moderación de ofertas laborales (HU-12) ────────────────────────────────


@router.get("/vacantes/pendientes", response_model=VacantePaginadaResponse)
def listar_vacantes_pendientes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: CurrentUser = Depends(_solo_admin),
    db: Session = Depends(get_db),
):
    return VacanteService(db).listar_pendientes_revision(page=page, page_size=page_size)


@router.post("/vacantes/{vacante_id}/decision", response_model=VacanteResponse)
def decidir_vacante(
    vacante_id: uuid.UUID,
    data: VacanteModeracionRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_admin),
    db: Session = Depends(get_db),
):
    # VacanteService.moderar ya registra su propia auditoria y hace commit,
    # siguiendo el mismo patron self-contained del resto del modulo vacantes.
    return VacanteService(db).moderar(
        vacante_id=vacante_id,
        aprobado=data.aprobado,
        motivo_rechazo=data.motivo_rechazo,
        current_user=current_user,
        ip_address=get_client_ip(request),
    )
