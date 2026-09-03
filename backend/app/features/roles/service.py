import uuid

from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException, ConflictException, ResourceNotFoundException
from app.features.bitacora.service import BitacoraService
from app.features.roles.repository import RolesRepository
from app.features.roles.schema import RolResponse, UsuarioAdminResponse

_ETIQUETAS_ESTADO = {
    "active": "activo",
    "pending_verification": "pendiente de verificación",
    "suspended": "suspendido",
    "blocked": "bloqueado",
}

# "empresa" existe como rol real (ver AuthService.registrar_empresa) pero no es asignable
# manualmente desde este panel: siempre se otorga junto con una fila de company_member,
# nunca de forma aislada.
_ROLES_ASIGNABLES = ("candidate", "moderator", "platform_admin")


class RolesService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RolesRepository(db)
        self.bitacora = BitacoraService(db)

    def listar_roles(self) -> list[RolResponse]:
        return [
            RolResponse(id=rol.id, nombre=rol.name, descripcion=rol.description)
            for rol in self.repo.listar_roles()
        ]

    def listar_usuarios(self) -> list[UsuarioAdminResponse]:
        usuarios = self.repo.listar_usuarios()
        ids = [usuario.id for usuario in usuarios]
        roles_por_usuario = self.repo.roles_de_usuarios(ids)
        miembros_empresa = self.repo.miembros_empresa_de(ids)
        return [
            self._a_dto(usuario, roles_por_usuario.get(usuario.id, []), usuario.id in miembros_empresa)
            for usuario in usuarios
        ]

    def asignar_rol(
        self,
        usuario_id: uuid.UUID | str,
        nombre_rol: str,
        responsable_id: uuid.UUID | str | None,
        ip: str | None = None,
    ) -> tuple[UsuarioAdminResponse, str | None]:
        if nombre_rol not in _ROLES_ASIGNABLES:
            raise BusinessException(f"El rol '{nombre_rol}' no es asignable desde el panel.")

        usuario = self.repo.obtener_usuario(usuario_id)
        if usuario is None:
            raise ResourceNotFoundException("No se encontró el usuario.")

        rol = self.repo.obtener_rol_por_nombre(nombre_rol)
        if rol is None:
            raise ResourceNotFoundException("No se encontró el rol indicado.")

        roles_anteriores = self.repo.roles_de_usuario(usuario.id)
        rol_anterior = roles_anteriores[0] if len(roles_anteriores) == 1 else (",".join(roles_anteriores) or None)

        if rol_anterior == nombre_rol:
            raise ConflictException("El usuario ya tiene asignado ese rol.")

        self.repo.reemplazar_roles(usuario.id, rol)

        self.bitacora.registrar(
            modulo="gestion_roles",
            accion="asignar_rol",
            usuario_id=responsable_id,
            ip=ip,
            detalles=f"usuario={usuario.email} rol_anterior={rol_anterior or 'sin rol'} rol_nuevo={nombre_rol}",
        )
        self.db.commit()

        return self._dto_individual(usuario), rol_anterior

    def _dto_individual(self, usuario) -> UsuarioAdminResponse:
        return self._a_dto(usuario, self.repo.roles_de_usuario(usuario.id), self.repo.es_miembro_empresa(usuario.id))

    def _a_dto(self, usuario, roles: list[str], es_miembro_empresa: bool) -> UsuarioAdminResponse:
        estado = _ETIQUETAS_ESTADO.get(usuario.account_status, usuario.account_status)
        return UsuarioAdminResponse(
            id=usuario.id,
            correo=usuario.email,
            estado=estado,
            fecha_registro=usuario.created_at,
            ultimo_acceso=usuario.last_login_at,
            roles=roles,
            es_miembro_empresa=es_miembro_empresa,
        )
