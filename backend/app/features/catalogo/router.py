from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.catalogo import CategoriaOferta, Carrera, Ciudad, Habilidad
from app.features.catalogo.schema import CarreraResponse, CategoriaOfertaResponse, CiudadResponse, HabilidadResponse

router = APIRouter(prefix="/catalogos", tags=["catalogos"])


@router.get("/carreras", response_model=list[CarreraResponse])
def listar_carreras(db: Session = Depends(get_db)):
    return db.scalars(select(Carrera).order_by(Carrera.nombre)).all()


@router.get("/habilidades", response_model=list[HabilidadResponse])
def listar_habilidades(db: Session = Depends(get_db)):
    return db.scalars(select(Habilidad).where(Habilidad.aprobada.is_(True)).order_by(Habilidad.nombre)).all()


@router.get("/categorias-oferta", response_model=list[CategoriaOfertaResponse])
def listar_categorias(db: Session = Depends(get_db)):
    return db.scalars(select(CategoriaOferta).order_by(CategoriaOferta.nombre)).all()


@router.get("/ciudades", response_model=list[CiudadResponse])
def listar_ciudades(db: Session = Depends(get_db)):
    return db.scalars(select(Ciudad).order_by(Ciudad.nombre)).all()
