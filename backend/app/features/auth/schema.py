from pydantic import BaseModel, EmailStr, Field

from app.models.enums import RolNombre


class LoginRequest(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    rol: RolNombre


class RegistroEgresadoRequest(BaseModel):
    nombres: str
    apellidos: str
    ci: str
    correo: EmailStr
    password: str = Field(min_length=8)
    carrera_id: int
    anio_egreso: int
    matricula: str | None = None


class RegistroEmpresaRequest(BaseModel):
    razon_social: str
    nit: str
    correo: EmailStr
    password: str = Field(min_length=8)
    sector: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    representante_legal: str | None = None


class MessageResponse(BaseModel):
    detail: str
