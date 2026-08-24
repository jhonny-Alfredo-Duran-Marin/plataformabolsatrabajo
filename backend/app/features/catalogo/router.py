from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.catalogo.schema import CarreraResponse, CategoriaOfertaResponse, CiudadResponse, HabilidadResponse
from app.features.catalogo.service import CatalogoService

router = APIRouter(prefix="/catalogos", tags=["catalogos"])


@router.get("/carreras", response_model=list[CarreraResponse])
def listar_carreras(db: Session = Depends(get_db)):
    return CatalogoService(db).listar_carreras()


@router.get("/habilidades", response_model=list[HabilidadResponse])
def listar_habilidades(db: Session = Depends(get_db)):
    return CatalogoService(db).listar_habilidades()


@router.get("/categorias-oferta", response_model=list[CategoriaOfertaResponse])
def listar_categorias(db: Session = Depends(get_db)):
    return CatalogoService(db).listar_categorias()


@router.get("/ciudades", response_model=list[CiudadResponse])
def listar_ciudades(db: Session = Depends(get_db)):
    return CatalogoService(db).listar_ciudades()
