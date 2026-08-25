import uuid

from pydantic import BaseModel


class CarreraResponse(BaseModel):
    id: uuid.UUID
    nombre: str
    facultad: str | None = None

    model_config = {"from_attributes": True}


class HabilidadResponse(BaseModel):
    id: uuid.UUID
    nombre: str

    model_config = {"from_attributes": True}


class CategoriaOfertaResponse(BaseModel):
    id: uuid.UUID
    nombre: str

    model_config = {"from_attributes": True}


class CiudadResponse(BaseModel):
    id: uuid.UUID | None = None
    nombre: str
