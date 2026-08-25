import uuid
from collections.abc import Iterable

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.common.exceptions import ForbiddenException, UnauthorizedException
from app.security.jwt_provider import decode_token

_bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Representa al usuario autenticado a partir del token JWT.

    rol es el rol principal (para compatibilidad con el frontend) y roles la
    lista completa asignada en user_role. Los usuarios de empresa sin fila en
    user_role reciben el rol sintético 'empresa'.
    """

    def __init__(self, id_usuario: uuid.UUID, rol: str, roles: list[str]) -> None:
        self.id_usuario = id_usuario
        self.rol = rol
        self.roles = roles

    @property
    def es_admin(self) -> bool:
        return "platform_admin" in self.roles


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise UnauthorizedException("No se proporcionó un token de autenticación.")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise UnauthorizedException("Token inválido o expirado.") from exc

    if payload.get("type") != "access":
        raise UnauthorizedException("El token proporcionado no es un token de acceso.")

    try:
        id_usuario = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError) as exc:
        raise UnauthorizedException("Token inválido.") from exc

    roles = [str(r) for r in payload.get("roles", [])] or [str(payload.get("rol", ""))]
    return CurrentUser(id_usuario=id_usuario, rol=str(payload.get("rol", "")), roles=roles)


def require_roles(*roles_permitidos: str):
    """Dependencia de autorización por rol, verificada en el servidor (RNF-06)."""

    def _checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not set(current_user.roles) & _as_set(roles_permitidos):
            raise ForbiddenException("No tiene permisos para acceder a este recurso.")
        return current_user

    return _checker


def _as_set(roles: Iterable[str]) -> set[str]:
    return set(roles)
