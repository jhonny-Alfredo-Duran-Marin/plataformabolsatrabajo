"""Reportes personalizados (requisito general 5): universidades, superadmin y empresas."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import AppException, ForbiddenException
from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.features.planes.limites import plan_vigente
from app.features.reportes.catalogo import Contexto
from app.features.reportes.interprete import InterpreteReportes
from app.features.reportes.schema import (
    CatalogoReportes,
    ConsultaReporte,
    EnviarReporte,
    EnvioReporteResponse,
    ExportarReporte,
    InterpretarReporte,
    ReporteInterpretado,
    VistaPreviaReporte,
)
from app.features.reportes.service import ReporteService
from app.models.empresa import CompanyMember
from app.models.usuario import AppUser
from app.security.dependencies import CurrentUser, get_current_user
from app.security.permisos import exigir_permiso
from app.security.tenant import AlcanceStaff, alcance_staff
from app.shared import ia_generativa
from app.shared.email_service import EmailService

router = APIRouter(prefix="/reportes", tags=["reportes"])

_ROLES_STAFF = {"platform_admin", "moderator"}


class PlanSinReportes(AppException):
    status_code = 402


class Solicitante:
    def __init__(
        self,
        contexto: Contexto,
        usuario: CurrentUser,
        correo: str | None,
        mensaje_plan: str | None,
        alcance: AlcanceStaff | None = None,
    ) -> None:
        self.contexto = contexto
        self.usuario = usuario
        self.correo = correo
        self.mensaje_plan = mensaje_plan
        # Solo el personal de la universidad; sus botones dependen de los permisos de su grupo.
        self.alcance = alcance

    def exigir(self, db: Session, codigo: str) -> None:
        if self.alcance is not None:
            exigir_permiso(db, self.alcance, codigo)


def get_solicitante(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> Solicitante:
    usuario = db.get(AppUser, current_user.id_usuario)
    correo = usuario.email if usuario else None
    if _ROLES_STAFF & set(current_user.roles):
        institucion = alcance_staff(db, current_user)
        alcance = AlcanceStaff(current_user, institucion)
        exigir_permiso(db, alcance, "menu.reportes")
        mensaje_plan = None
        plan = plan_vigente(db, institucion) if institucion else None
        if plan is not None and not plan.employability_reports:
            mensaje_plan = (
                f"El plan {plan.name} de tu universidad no incluye reportes personalizados. "
                "Están disponibles en los planes Profesional e Institucional."
            )
        return Solicitante(
            Contexto(rol="staff", institution_id=institucion), current_user, correo, mensaje_plan, alcance
        )
    if "empresa" in current_user.roles:
        company_id = db.scalar(
            select(CompanyMember.company_id).where(
                CompanyMember.user_id == current_user.id_usuario, CompanyMember.is_active.is_(True)
            )
        )
        if company_id is not None:
            return Solicitante(Contexto(rol="empresa", company_id=company_id), current_user, correo, None)
    raise ForbiddenException("Los reportes están disponibles para universidades y empresas.")


def _habilitado(solicitante: Solicitante) -> Solicitante:
    if solicitante.mensaje_plan:
        raise PlanSinReportes(solicitante.mensaje_plan)
    return solicitante


def get_habilitado(solicitante: Solicitante = Depends(get_solicitante)) -> Solicitante:
    return _habilitado(solicitante)


@router.get("/fuentes", response_model=CatalogoReportes)
def catalogo(solicitante: Solicitante = Depends(get_solicitante), db: Session = Depends(get_db)):
    return CatalogoReportes(
        fuentes=ReporteService(db).catalogo(solicitante.contexto),
        correo_disponible=EmailService().configurado(),
        plan_permite=solicitante.mensaje_plan is None,
        mensaje_plan=solicitante.mensaje_plan,
        ia_disponible=ia_generativa.disponible("reportes"),
    )


@router.post("/interpretar", response_model=ReporteInterpretado)
def interpretar(
    pedido: InterpretarReporte,
    solicitante: Solicitante = Depends(get_habilitado),
    db: Session = Depends(get_db),
):
    """Arma la consulta a partir de un pedido escrito o dictado, con Gemini; no la ejecuta."""
    return InterpreteReportes(db).interpretar(solicitante.contexto, pedido.pedido)


@router.post("/vista-previa", response_model=VistaPreviaReporte)
def vista_previa(
    consulta: ConsultaReporte,
    pagina: int = Query(1, ge=1),
    tamanio: int = Query(25, ge=1, le=100),
    solicitante: Solicitante = Depends(get_habilitado),
    db: Session = Depends(get_db),
):
    return ReporteService(db).vista_previa(solicitante.contexto, consulta, pagina, tamanio)


@router.post("/exportar")
def exportar(
    consulta: ExportarReporte,
    request: Request,
    solicitante: Solicitante = Depends(get_habilitado),
    db: Session = Depends(get_db),
):
    solicitante.exigir(db, "boton.reportes.exportar")
    archivo = ReporteService(db).exportar(
        solicitante.contexto, consulta, solicitante.correo, solicitante.usuario.id_usuario, get_client_ip(request)
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


@router.post("/enviar", response_model=EnvioReporteResponse)
def enviar(
    consulta: EnviarReporte,
    request: Request,
    solicitante: Solicitante = Depends(get_habilitado),
    db: Session = Depends(get_db),
):
    solicitante.exigir(db, "boton.reportes.correo")
    destinatarios = ReporteService(db).enviar(
        solicitante.contexto, consulta, solicitante.correo, solicitante.usuario.id_usuario, get_client_ip(request)
    )
    cantidad = "1 destinatario" if len(destinatarios) == 1 else f"{len(destinatarios)} destinatarios"
    return EnvioReporteResponse(mensaje=f"Reporte enviado a {cantidad}.", destinatarios=destinatarios)
