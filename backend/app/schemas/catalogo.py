from pydantic import BaseModel


class CarreraResponse(BaseModel):
    id: int
    nombre: str
    facultad: str | None

    model_config = {"from_attributes": True}


class HabilidadResponse(BaseModel):
    id: int
    nombre: str

    model_config = {"from_attributes": True}


class CategoriaOfertaResponse(BaseModel):
    id: int
    nombre: str

    model_config = {"from_attributes": True}


class CiudadResponse(BaseModel):
    id: int
    nombre: str

    model_config = {"from_attributes": True}
