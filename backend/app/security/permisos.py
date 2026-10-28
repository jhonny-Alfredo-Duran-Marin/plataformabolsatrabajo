"""Privilegios por componente de la interfaz (requisito general 2).

Cada componente del panel de administración (menú, formulario, botón o etiqueta) tiene
un código. Un usuario del personal de una universidad recibe:

- Sin grupos: los componentes que su rol tiene por defecto (lo que veía antes de existir
  los grupos).
- Con uno o más grupos: la unión de los permisos de sus grupos. Así un grupo puede tanto
  quitar como agregar componentes.

En los dos casos el rol pone el techo: un moderador nunca recibe un componente marcado
solo para administradores, aunque su grupo lo tenga. El superadmin del SaaS lo ve todo y
los grupos no lo afectan, y el administrador de la universidad conserva siempre «Grupos y
permisos» para no quedar bloqueado fuera de su propio panel.

El backend comprueba el permiso en cada endpoint (requiere_permiso), no solo la interfaz.
"""

import uuid
from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import ForbiddenException
from app.core.database import get_db
from app.models.grupo import UserGroup, UserGroupMember, UserGroupPermission
from app.security.tenant import AlcanceStaff, get_alcance_staff

ADMIN = "platform_admin"
MODERADOR = "moderator"
_STAFF = frozenset({ADMIN, MODERADOR})
_AMBOS = _STAFF
_SOLO_ADMIN = frozenset({ADMIN})


@dataclass(frozen=True)
class Componente:
    codigo: str
    tipo: str  # menu | formulario | boton | etiqueta
    modulo: str
    nombre: str
    descripcion: str
    por_defecto: frozenset[str]
    asignable_a: frozenset[str]


def _c(codigo, tipo, modulo, nombre, descripcion, por_defecto=_AMBOS, asignable_a=_AMBOS) -> Componente:
    return Componente(codigo, tipo, modulo, nombre, descripcion, frozenset(por_defecto), frozenset(asignable_a))


CATALOGO: tuple[Componente, ...] = (
    _c("menu.dashboard", "menu", "Dashboard", "Dashboard", "Panel de inicio con lo pendiente y el resumen."),
    _c("etiqueta.dashboard.indicadores", "etiqueta", "Dashboard", "Indicadores",
       "Tarjetas con egresados, empresas, vacantes y postulaciones."),
    _c("etiqueta.dashboard.actividad", "etiqueta", "Dashboard", "Actividad reciente",
       "Últimas acciones de la bitácora y accesos del día."),
    _c("menu.universidades", "menu", "Mi universidad", "Mi universidad y plan",
       "Plan contratado, uso y pagos de la universidad.", _SOLO_ADMIN, _SOLO_ADMIN),
    _c("menu.usuarios", "menu", "Usuarios", "Gestión de roles", "Lista de usuarios y el rol de cada uno.",
       _SOLO_ADMIN, _SOLO_ADMIN),
    _c("formulario.usuarios.nuevo", "formulario", "Usuarios", "Nuevo usuario",
       "Alta de moderadores con contraseña inicial.", _SOLO_ADMIN, _SOLO_ADMIN),
    _c("boton.usuarios.cambiar_rol", "boton", "Usuarios", "Guardar rol", "Cambiar el rol de un usuario.",
       _SOLO_ADMIN, _SOLO_ADMIN),
    _c("menu.grupos", "menu", "Usuarios", "Grupos y permisos",
       "Crear grupos y elegir qué componentes ve cada uno.", _SOLO_ADMIN, _SOLO_ADMIN),
    _c("menu.validacion", "menu", "Validación de egresados", "Validación de egresados",
       "Lista de egresados pendientes de validar."),
    _c("boton.validacion.decidir", "boton", "Validación de egresados", "Aprobar / rechazar egresado",
       "Decidir sobre la cuenta de un egresado."),
    _c("menu.empresas", "menu", "Gestión de empresas", "Gestión de empresas",
       "Empresas que reclutan en la universidad."),
    _c("boton.empresas.validar", "boton", "Gestión de empresas", "Aprobar / rechazar empresa",
       "Decidir sobre una empresa pendiente."),
    _c("formulario.empresas.configuracion", "formulario", "Gestión de empresas", "Notificaciones y postulaciones",
       "Interruptores de configuración de cada empresa."),
    _c("boton.empresas.baja", "boton", "Gestión de empresas", "Desactivar / reactivar empresa",
       "Baja lógica de una empresa y su reactivación."),
    _c("menu.moderacion", "menu", "Moderación de ofertas", "Moderación de ofertas", "Ofertas que esperan revisión."),
    _c("boton.moderacion.decidir", "boton", "Moderación de ofertas", "Aprobar / rechazar oferta",
       "Publicar o rechazar una oferta."),
    _c("menu.denuncias", "menu", "Denuncias de ofertas", "Denuncias de ofertas", "Ofertas denunciadas por egresados."),
    _c("boton.denuncias.resolver", "boton", "Denuncias de ofertas", "Resolver denuncia",
       "Mantener, suspender o eliminar una oferta denunciada."),
    _c("menu.reportes", "menu", "Reportes", "Reportes personalizados", "Armar y ver reportes en pantalla."),
    _c("boton.reportes.exportar", "boton", "Reportes", "Exportar reporte", "Descargar en Excel, PDF o HTML."),
    _c("boton.reportes.correo", "boton", "Reportes", "Enviar reporte por correo", "Mandar el reporte por correo."),
    _c("menu.encuestas", "menu", "Encuestas laborales", "Encuestas de situación laboral",
       "Encuestas enviadas a los egresados y su porcentaje de respuesta."),
    _c("boton.encuestas.enviar", "boton", "Encuestas laborales", "Enviar / cerrar encuesta",
       "Configurar una encuesta, enviarla a los egresados y cerrarla.", _SOLO_ADMIN, _SOLO_ADMIN),
    _c("menu.colocaciones", "menu", "Colocaciones", "Registro de colocaciones",
       "Contrataciones de egresados registradas y las que la plataforma sugiere.", _SOLO_ADMIN, _SOLO_ADMIN),
    _c("boton.colocaciones.registrar", "boton", "Colocaciones", "Registrar / editar / confirmar colocación",
       "Registrar una contratación, corregirla o confirmar la que sugiere la plataforma.", _SOLO_ADMIN, _SOLO_ADMIN),
    _c("boton.colocaciones.eliminar", "boton", "Colocaciones", "Eliminar colocación",
       "Dar de baja una colocación indicando el motivo.", _SOLO_ADMIN, _SOLO_ADMIN),
    _c("menu.bitacora", "menu", "Bitácora", "Bitácora del sistema",
       "Consultar la bitácora con la clave de desarrollador."),
    _c("boton.bitacora.exportar", "boton", "Bitácora", "Exportar bitácora", "Descargar la bitácora en Excel o PDF."),
    _c("menu.alertas", "menu", "Centro de alertas", "Centro de alertas", "Avisos y notificaciones del panel."),
)

COMPONENTES: dict[str, Componente] = {c.codigo: c for c in CATALOGO}
TODOS: frozenset[str] = frozenset(COMPONENTES)
# El administrador de la universidad no puede quitarse a sí mismo la pantalla de grupos.
SIEMPRE_ADMIN: frozenset[str] = frozenset({"menu.grupos"})


def grupos_de(db: Session, usuario_id: uuid.UUID, institution_id: uuid.UUID | None) -> list[uuid.UUID]:
    if institution_id is None:
        return []
    return list(
        db.scalars(
            select(UserGroupMember.group_id)
            .join(UserGroup, UserGroup.id == UserGroupMember.group_id)
            .where(UserGroupMember.user_id == usuario_id, UserGroup.institution_id == institution_id)
        )
    )


def permisos_de_usuario(
    db: Session, usuario_id: uuid.UUID, roles: list[str] | set[str], institution_id: uuid.UUID | None
) -> frozenset[str]:
    """Componentes que puede usar un usuario. institution_id=None en un admin = superadmin."""
    roles_staff = _STAFF & set(roles)
    if not roles_staff:
        return frozenset()
    if ADMIN in roles_staff and institution_id is None:
        return TODOS

    grupos = grupos_de(db, usuario_id, institution_id)
    if grupos:
        base = set(
            db.scalars(select(UserGroupPermission.permission_code).where(UserGroupPermission.group_id.in_(grupos)))
        )
    else:
        base = {c.codigo for c in CATALOGO if c.por_defecto & roles_staff}
    efectivos = {codigo for codigo in base if codigo in COMPONENTES and COMPONENTES[codigo].asignable_a & roles_staff}
    if ADMIN in roles_staff:
        efectivos |= SIEMPRE_ADMIN
    return frozenset(efectivos)


def permisos_de(db: Session, alcance: AlcanceStaff) -> frozenset[str]:
    return permisos_de_usuario(db, alcance.usuario.id_usuario, alcance.usuario.roles, alcance.institution_id)


def exigir_permiso(db: Session, alcance: AlcanceStaff, *codigos: str) -> None:
    """Exige al menos uno de los componentes indicados."""
    if not permisos_de(db, alcance) & set(codigos):
        raise ForbiddenException(f"Tu grupo de usuarios no tiene permiso para «{COMPONENTES[codigos[0]].nombre}».")


def requiere_permiso(*codigos: str):
    """Dependencia: personal de la universidad con permiso sobre alguno de los componentes."""
    desconocidos = [c for c in codigos if c not in COMPONENTES]
    if not codigos or desconocidos:
        raise ValueError(f"Componentes desconocidos: {desconocidos}")

    def _dependencia(alcance: AlcanceStaff = Depends(get_alcance_staff), db: Session = Depends(get_db)) -> AlcanceStaff:
        exigir_permiso(db, alcance, *codigos)
        return alcance

    return _dependencia
