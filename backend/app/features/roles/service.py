import uuid

from sqlalchemy.orm import Session

from app.common.exceptions import (
    BusinessException,
    ConflictException,
    ForbiddenException,
    ResourceNotFoundException,
)
from app.features.auth.repository import UsuarioRepository
from app.features.bitacora.service import BitacoraService
from app.features.planes.limites import verificar_cupo_moderadores
from app.features.roles.repository import RolesRepository
from app.features.roles.schema import CrearUsuarioStaffRequest, RolResponse, UsuarioAdminResponse
from app.models.institucion import Institution
from app.models.usuario import AppUser
from app.security.password_hasher import hash_password

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
# Lo que asigna el admin de una universidad: igual que al crear staff, los administradores los nombra el superadmin.
_ROLES_DE_UNIVERSIDAD = ("candidate", "moderator")


class RolesService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RolesRepository(db)
        self.bitacora = BitacoraService(db)

    def listar_roles(self, institution_id: uuid.UUID | None = None) -> list[RolResponse]:
        """Roles que el panel puede asignar (el de empresa no se asigna a mano).

        El admin de una universidad no nombra administradores: eso es del superadmin.
        """
        asignables = _ROLES_ASIGNABLES if institution_id is None else _ROLES_DE_UNIVERSIDAD
        return [
            RolResponse(id=rol.id, nombre=rol.name, descripcion=rol.description)
            for rol in self.repo.listar_roles()
            if rol.name in asignables
        ]

    def listar_usuarios(self, institution_id: uuid.UUID | None = None) -> list[UsuarioAdminResponse]:
        usuarios = self.repo.listar_usuarios(institution_id)
        ids = [usuario.id for usuario in usuarios]
        roles_por_usuario = self.repo.roles_de_usuarios(ids)
        miembros_empresa = self.repo.miembros_empresa_de(ids)
        inst_egresados = self.repo.instituciones_de_egresados(ids)
        inst_por_usuario = {u.id: u.institution_id or inst_egresados.get(u.id) for u in usuarios}
        nombres = self.repo.nombres_instituciones({i for i in inst_por_usuario.values() if i})
        return [
            self._a_dto(
                usuario,
                roles_por_usuario.get(usuario.id, []),
                usuario.id in miembros_empresa,
                inst_por_usuario[usuario.id],
                nombres,
            )
            for usuario in usuarios
        ]

    def asignar_rol(
        self,
        usuario_id: uuid.UUID | str,
        nombre_rol: str,
        responsable_id: uuid.UUID | str | None,
        ip: str | None = None,
        institution_id: uuid.UUID | None = None,
    ) -> tuple[UsuarioAdminResponse, str | None]:
        if nombre_rol not in _ROLES_ASIGNABLES:
            raise BusinessException(f"El rol '{nombre_rol}' no es asignable desde el panel.")

        usuario = self.repo.obtener_usuario(usuario_id, institution_id)
        if usuario is None:
            raise ResourceNotFoundException("No se encontró el usuario.")
        if self.repo.es_miembro_empresa(usuario.id):
            # Quitarle el rol de empresa le cortaría el acceso a su empresa.
            raise BusinessException("Las cuentas de empresa se gestionan desde Gestión de empresas.")
        if institution_id is not None and (
            nombre_rol not in _ROLES_DE_UNIVERSIDAD or "platform_admin" in self.repo.roles_de_usuario(usuario.id)
        ):
            # Sin esto, el admin de una universidad se saltaría el límite del plan nombrando co-administradores.
            raise ForbiddenException("Solo el superadministrador puede nombrar o cambiar administradores de universidad.")

        if nombre_rol in ("moderator", "platform_admin"):
            # El staff queda atado a una universidad; solo un platform_admin sin universidad
            # es superadmin, y ese caso nunca se produce desde el panel de una universidad.
            usuario.institution_id = (
                institution_id or usuario.institution_id or self.repo.institucion_de_egresado(usuario.id)
            )

        rol = self.repo.obtener_rol_por_nombre(nombre_rol)
        if rol is None:
            raise ResourceNotFoundException("No se encontró el rol indicado.")

        roles_anteriores = self.repo.roles_de_usuario(usuario.id)
        rol_anterior = roles_anteriores[0] if len(roles_anteriores) == 1 else (",".join(roles_anteriores) or None)

        if rol_anterior == nombre_rol:
            raise ConflictException("El usuario ya tiene asignado ese rol.")
        if nombre_rol == "moderator" and usuario.institution_id is not None:
            verificar_cupo_moderadores(self.db, usuario.institution_id)

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

    def crear_usuario_staff(
        self,
        data: CrearUsuarioStaffRequest,
        responsable_id: uuid.UUID | str | None,
        ip: str | None = None,
        institution_id: uuid.UUID | None = None,
    ) -> UsuarioAdminResponse:
        """Crea un admin o moderador con contraseña inicial, atado a una universidad.

        El superadmin (institution_id=None) elige la universidad y el rol; el admin de una
        universidad solo crea moderadores de la suya. Nunca se crea otro superadmin.
        """
        if institution_id is not None:
            if data.rol != "moderator":
                raise ForbiddenException("Solo el superadministrador puede crear administradores de universidad.")
            destino = institution_id
        elif data.institucion_id is None:
            raise BusinessException("Indicá la universidad a la que pertenece el usuario.")
        else:
            destino = data.institucion_id

        institucion = self.db.get(Institution, destino)
        if institucion is None or not institucion.is_tenant:
            raise ConflictException("La universidad indicada no está habilitada en la plataforma.")
        if UsuarioRepository(self.db).existe_correo(data.correo):
            raise ConflictException("Ya existe una cuenta con ese correo.")
        if data.rol == "moderator":
            verificar_cupo_moderadores(self.db, institucion.id)
        rol = self.repo.obtener_rol_por_nombre(data.rol)
        if rol is None:
            raise ResourceNotFoundException("No se encontró el rol indicado.")

        usuario = AppUser(
            email=data.correo.strip().lower(),
            password_hash=hash_password(data.password),
            account_status="active",
            institution_id=institucion.id,
            # El admin conoce la contraseña inicial: la persona la reemplaza en su primer ingreso.
            must_change_password=True,
        )
        self.db.add(usuario)
        self.db.flush()
        self.repo.reemplazar_roles(usuario.id, rol)

        self.bitacora.registrar(
            modulo="gestion_roles",
            accion="crear_usuario",
            usuario_id=responsable_id,
            ip=ip,
            detalles=f"usuario={usuario.email} rol={data.rol} institucion={institucion.id}",
        )
        self.db.commit()

        return self._a_dto(usuario, [data.rol], False, institucion.id, {institucion.id: institucion.name})

    def _dto_individual(self, usuario) -> UsuarioAdminResponse:
        institucion = usuario.institution_id or self.repo.institucion_de_egresado(usuario.id)
        return self._a_dto(
            usuario,
            self.repo.roles_de_usuario(usuario.id),
            self.repo.es_miembro_empresa(usuario.id),
            institucion,
            self.repo.nombres_instituciones({institucion} if institucion else set()),
        )

    def _a_dto(
        self,
        usuario,
        roles: list[str],
        es_miembro_empresa: bool,
        institucion_id: uuid.UUID | None,
        nombres_instituciones: dict[uuid.UUID, str],
    ) -> UsuarioAdminResponse:
        estado = _ETIQUETAS_ESTADO.get(usuario.account_status, usuario.account_status)
        return UsuarioAdminResponse(
            id=usuario.id,
            correo=usuario.email,
            estado=estado,
            fecha_registro=usuario.created_at,
            ultimo_acceso=usuario.last_login_at,
            roles=roles,
            es_miembro_empresa=es_miembro_empresa,
            institucion_id=institucion_id,
            institucion=nombres_instituciones.get(institucion_id) if institucion_id else None,
        )
