import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.features.roles.schema import AsignarRolRequest, AsignarRolResponse, RolResponse, UsuarioAdminResponse
from app.security.dependencies import CurrentUser, require_roles
from app.features.roles.service import RolesService

router = APIRouter(prefix="/admin", tags=["gestion-roles"])

_solo_admin = require_roles("platform_admin")


@router.get("/roles", response_model=list[RolResponse], dependencies=[Depends(_solo_admin)])
def listar_roles(db: Session = Depends(get_db)):
    return RolesService(db).listar_roles()


@router.get("/usuarios", response_model=list[UsuarioAdminResponse], dependencies=[Depends(_solo_admin)])
def listar_usuarios(db: Session = Depends(get_db)):
    return RolesService(db).listar_usuarios()


@router.put("/usuarios/{usuario_id}/rol", response_model=AsignarRolResponse)
def asignar_rol(
    usuario_id: uuid.UUID,
    data: AsignarRolRequest,
    request: Request,
    current_user: CurrentUser = Depends(_solo_admin),
    db: Session = Depends(get_db),
):
    usuario, rol_anterior = RolesService(db).asignar_rol(
        usuario_id=usuario_id,
        nombre_rol=data.rol,
        responsable_id=current_user.id_usuario,
        ip=get_client_ip(request),
    )
    return AsignarRolResponse(
        usuario=usuario,
        rol_anterior=rol_anterior,
        detalle="Rol actualizado. El usuario deberá iniciar sesión de nuevo para obtener los nuevos permisos.",
    )
