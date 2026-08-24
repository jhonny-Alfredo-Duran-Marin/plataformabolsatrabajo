import uuid
from datetime import datetime

from pydantic import BaseModel


class RolResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    descripcion: str | None = None


class UsuarioAdminResponse(BaseModel):
    id: uuid.UUID
    correo: str
    estado: str
    fecha_registro: datetime
    ultimo_acceso: datetime | None = None
    roles: list[str] = []
    es_miembro_empresa: bool = False


class AsignarRolRequest(BaseModel):
    rol: str


class AsignarRolResponse(BaseModel):
    usuario: UsuarioAdminResponse
    rol_anterior: str | None
    detalle: str
