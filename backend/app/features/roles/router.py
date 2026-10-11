import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.common.request_context import get_client_ip
from app.core.database import get_db
from app.features.roles.schema import (
    AsignarRolRequest,
    AsignarRolResponse,
    CrearUsuarioStaffRequest,
    RolResponse,
    UsuarioAdminResponse,
)
from app.security.permisos import requiere_permiso
from app.security.tenant import AlcanceStaff
from app.features.roles.service import RolesService

router = APIRouter(prefix="/admin", tags=["gestion-roles"])

# Componentes del panel «Gestión de roles»; el catálogo los reserva a administradores.
_ve_usuarios = requiere_permiso("menu.usuarios")


@router.get("/roles", response_model=list[RolResponse])
def listar_roles(alcance: AlcanceStaff = Depends(_ve_usuarios), db: Session = Depends(get_db)):
    return RolesService(db).listar_roles(alcance.institution_id)


@router.get("/usuarios", response_model=list[UsuarioAdminResponse])
def listar_usuarios(alcance: AlcanceStaff = Depends(_ve_usuarios), db: Session = Depends(get_db)):
    return RolesService(db).listar_usuarios(alcance.institution_id)


@router.post("/usuarios", response_model=UsuarioAdminResponse, status_code=201)
def crear_usuario_staff(
    data: CrearUsuarioStaffRequest,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("formulario.usuarios.nuevo")),
    db: Session = Depends(get_db),
):
    return RolesService(db).crear_usuario_staff(
        data,
        responsable_id=alcance.usuario.id_usuario,
        ip=get_client_ip(request),
        institution_id=alcance.institution_id,
    )


@router.put("/usuarios/{usuario_id}/rol", response_model=AsignarRolResponse)
def asignar_rol(
    usuario_id: uuid.UUID,
    data: AsignarRolRequest,
    request: Request,
    alcance: AlcanceStaff = Depends(requiere_permiso("boton.usuarios.cambiar_rol")),
    db: Session = Depends(get_db),
):
    usuario, rol_anterior = RolesService(db).asignar_rol(
        usuario_id=usuario_id,
        nombre_rol=data.rol,
        responsable_id=alcance.usuario.id_usuario,
        ip=get_client_ip(request),
        institution_id=alcance.institution_id,
    )
    return AsignarRolResponse(
        usuario=usuario,
        rol_anterior=rol_anterior,
        detalle="Rol actualizado. El usuario deberá iniciar sesión de nuevo para obtener los nuevos permisos.",
    )
