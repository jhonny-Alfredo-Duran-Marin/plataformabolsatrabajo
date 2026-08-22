from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import RolNombre
from app.schemas.auditoria import AuditoriaLogResponse
from app.security.dependencies import require_roles
from app.services.auditoria_service import AuditoriaService

router = APIRouter(prefix="/auditoria", tags=["auditoria"])

_solo_admin = require_roles(RolNombre.ADMINISTRADOR)


@router.get("", response_model=list[AuditoriaLogResponse], dependencies=[Depends(_solo_admin)])
def listar_bitacora(
    usuario_id: int | None = None,
    modulo: str | None = None,
    accion: str | None = None,
    db: Session = Depends(get_db),
):
    return AuditoriaService(db).listar(usuario_id=usuario_id, modulo=modulo, accion=accion)
