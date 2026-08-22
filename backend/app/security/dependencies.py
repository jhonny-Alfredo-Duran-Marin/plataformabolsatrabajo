from collections.abc import Iterable

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.common.exceptions import ForbiddenException, UnauthorizedException
from app.models.enums import RolNombre
from app.security.jwt_provider import decode_token

_bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Representa al usuario autenticado a partir del token JWT (equivalente a JwtAuthDetails)."""

    def __init__(self, id_usuario: int, rol: RolNombre) -> None:
        self.id_usuario = id_usuario
        self.rol = rol


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

    return CurrentUser(id_usuario=int(payload["sub"]), rol=RolNombre(payload["rol"]))


def require_roles(*roles_permitidos: RolNombre):
    """Dependencia de autorización por rol, verificada en el servidor (RNF-06)."""

    def _checker(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.rol not in _as_set(roles_permitidos):
            raise ForbiddenException("No tiene permisos para acceder a este recurso.")
        return current_user

    return _checker


def _as_set(roles: Iterable[RolNombre]) -> set[RolNombre]:
    return set(roles)
