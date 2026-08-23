from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.models.enums import RolNombre
from app.schemas.egresado import PerfilEgresadoResponse, ValidacionEgresadoDecisionRequest
from app.schemas.empresa import DecisionEmpresaRequest, EmpresaResponse, SuspensionEmpresaRequest
from app.security.dependencies import CurrentUser, require_roles
from app.services.bitacora_service import BitacoraService
from app.services.egresado_service import EgresadoService
from app.services.empresa_service import EmpresaService

router = APIRouter(prefix="/validacion", tags=["validacion-institucional"])

_solo_admin = require_roles(RolNombre.ADMINISTRADOR)


@router.get("/egresados/pendientes", response_model=list[PerfilEgresadoResponse])
def listar_egresados_pendientes(current_user: CurrentUser = Depends(_solo_admin), db: Session = Depends(get_db)):
    return EgresadoService(db).listar_pendientes_validacion()


@router.post("/egresados/{perfil_id}/decision", response_model=PerfilEgresadoResponse)
def decidir_egresado(
    perfil_id: int,
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


@router.post("/empresas/{empresa_id}/decision", response_model=EmpresaResponse)
def decidir_empresa(
    empresa_id: int,
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
    empresa_id: int,
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
