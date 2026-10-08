import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
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
from app.security.permisos import requiere_permiso
from app.security.tenant import AlcanceStaff
from app.features.bitacora.service import BitacoraService
from app.features.perfil.service import EgresadoService
from app.features.empresa.service import EmpresaService
from app.features.vacantes.router import avisar_si_se_publico
from app.features.vacantes.schema import VacanteModeracionRequest, VacantePaginadaResponse, VacanteResponse
from app.features.vacantes.service import VacanteService

router = APIRouter(prefix="/validacion", tags=["validacion-institucional"])

# Todos los endpoints operan dentro de la universidad del admin/moderador
# (alcance.institution_id); solo el superadmin (institution_id=None) actúa globalmente.


def _auditar(db: Session, request: Request, alcance: AlcanceStaff, accion: str, detalles: str) -> None:
    BitacoraService(db).registrar(
        modulo="validacion_institucional",
        accion=accion,
        usuario_id=alcance.usuario.id_usuario,
        ip=get_client_ip(request),
        detalles=f"{detalles} institucion={alcance.institution_id or 'global'}",
    )
    db.commit()


@router.get("/egresados/pendientes", response_model=list[PerfilEgresadoResponse])
def listar_egresados_pendientes(
    alcance: AlcanceStaff = Depends(requiere_permiso("menu.validacion")), db: Session = Depends(get_db)
):
    return EgresadoService(db).listar_pendientes_validacion(alcance.institution_id)


@router.post("/egresados/{perfil_id}/decision", response_model=PerfilEgresadoResponse)
def decidir_egresado(
    perfil_id: uuid.UUID,
    data: ValidacionEgresadoDecisionRequest,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.validacion.decidir")),
    db: Session = Depends(get_db),
):
    perfil = EgresadoService(db).validar(perfil_id, data.aprobado, data.motivo_rechazo, alcance.institution_id)
    _auditar(db, request, alcance, "decidir_egresado", f"perfil_id={perfil_id} aprobado={data.aprobado}")
    return perfil


@router.get("/empresas/pendientes", response_model=list[EmpresaResponse])
def listar_empresas_pendientes(
    alcance: AlcanceStaff = Depends(requiere_permiso("menu.empresas")), db: Session = Depends(get_db)
):
    return EmpresaService(db).listar_pendientes(alcance.institution_id)


@router.get("/empresas", response_model=list[EmpresaResponse])
def listar_todas_las_empresas(
    incluir_inactivas: bool = Query(default=False),
    alcance: AlcanceStaff = Depends(requiere_permiso("menu.empresas")),
    db: Session = Depends(get_db),
):
    return EmpresaService(db).listar_todas(incluir_inactivas=incluir_inactivas, institution_id=alcance.institution_id)


@router.post("/empresas/{empresa_id}/decision", response_model=EmpresaResponse)
def decidir_empresa(
    empresa_id: uuid.UUID,
    data: DecisionEmpresaRequest,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.empresas.validar")),
    db: Session = Depends(get_db),
):
    empresa = EmpresaService(db).decidir(
        empresa_id, data.aprobado, data.motivo_rechazo, alcance.institution_id, alcance.usuario.id_usuario
    )
    _auditar(db, request, alcance, "decidir_empresa", f"empresa_id={empresa_id} aprobado={data.aprobado}")
    return empresa


@router.post("/empresas/{empresa_id}/suspender", response_model=EmpresaResponse)
def suspender_empresa(
    empresa_id: uuid.UUID,
    data: SuspensionEmpresaRequest,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.empresas.baja")),
    db: Session = Depends(get_db),
):
    empresa = EmpresaService(db).suspender(empresa_id, data.motivo, alcance.institution_id, alcance.usuario.id_usuario)
    _auditar(db, request, alcance, "suspender_empresa", f"empresa_id={empresa_id}")
    return empresa


@router.patch("/empresas/{empresa_id}/configuracion", response_model=EmpresaResponse)
def configurar_empresa(
    empresa_id: uuid.UUID,
    data: ConfiguracionEmpresaRequest,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("formulario.empresas.configuracion")),
    db: Session = Depends(get_db),
):
    empresa = EmpresaService(db).actualizar_configuracion(
        empresa_id,
        notificaciones_activas=data.notificaciones_activas,
        postulaciones_activas=data.postulaciones_activas,
        institution_id=alcance.institution_id,
    )
    _auditar(
        db,
        request,
        alcance,
        "configurar_empresa",
        f"empresa_id={empresa_id} notificaciones={data.notificaciones_activas} postulaciones={data.postulaciones_activas}",
    )
    return empresa


@router.delete("/empresas/{empresa_id}", response_model=EmpresaResponse)
def eliminar_empresa_logico(
    empresa_id: uuid.UUID,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.empresas.baja")),
    db: Session = Depends(get_db),
):
    empresa = EmpresaService(db).eliminar_logico(empresa_id, alcance.institution_id, alcance.usuario.id_usuario)
    _auditar(db, request, alcance, "eliminar_empresa_logico", f"empresa_id={empresa_id}")
    return empresa


@router.post("/empresas/{empresa_id}/restaurar", response_model=EmpresaResponse)
def restaurar_empresa(
    empresa_id: uuid.UUID,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.empresas.baja")),
    db: Session = Depends(get_db),
):
    empresa = EmpresaService(db).restaurar(empresa_id, alcance.institution_id, alcance.usuario.id_usuario)
    _auditar(db, request, alcance, "restaurar_empresa", f"empresa_id={empresa_id}")
    return empresa


# ─── Moderación de ofertas laborales (HU-12) ────────────────────────────────


@router.get("/vacantes/pendientes", response_model=VacantePaginadaResponse)
def listar_vacantes_pendientes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    alcance: AlcanceStaff = Depends(requiere_permiso("menu.moderacion")),
    db: Session = Depends(get_db),
):
    return VacanteService(db).listar_pendientes_revision(
        page=page, page_size=page_size, institution_id=alcance.institution_id
    )


@router.post("/vacantes/{vacante_id}/decision", response_model=VacanteResponse)
def decidir_vacante(
    vacante_id: uuid.UUID,
    data: VacanteModeracionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.moderacion.decidir")),
    db: Session = Depends(get_db),
):
    # VacanteService.moderar ya registra su propia auditoria y hace commit,
    # siguiendo el mismo patron self-contained del resto del modulo vacantes.
    servicio = VacanteService(db)
    respuesta = servicio.moderar(
        vacante_id=vacante_id,
        aprobado=data.aprobado,
        motivo_rechazo=data.motivo_rechazo,
        current_user=alcance.usuario,
        ip_address=get_client_ip(request),
        institution_id=alcance.institution_id,
    )
    # Al aprobarla queda publicada: los egresados afines reciben el aviso en el momento.
    avisar_si_se_publico(servicio, background_tasks)
    return respuesta
