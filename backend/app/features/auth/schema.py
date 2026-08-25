import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    rol: str
    roles: list[str] = []


class RegistroEgresadoRequest(BaseModel):
    nombres: str = Field(min_length=1, max_length=100)
    apellidos: str = Field(min_length=1, max_length=100)
    ci: str = Field(min_length=5, max_length=50)
    correo: EmailStr
    password: str = Field(min_length=8)
    carrera_id: uuid.UUID | None = None
    anio_egreso: int | None = None
    matricula: str | None = None


class RegistroEmpresaRequest(BaseModel):
    razon_social: str = Field(min_length=1, max_length=250)
    nit: str = Field(min_length=3, max_length=50)
    correo: EmailStr
    password: str = Field(min_length=8)
    sector: str | None = None
    tamanio: str | None = None
    ciudad: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    sitio_web: str | None = None
    descripcion: str | None = None
    representante_legal: str | None = None


class MessageResponse(BaseModel):
    detail: str
