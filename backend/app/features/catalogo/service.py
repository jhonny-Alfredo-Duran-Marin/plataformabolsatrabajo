from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.features.catalogo.schema import (
    CarreraResponse,
    CategoriaOfertaResponse,
    CiudadResponse,
    HabilidadResponse,
)
from app.models.candidato import CandidateProfile
from app.models.catalogo import FieldOfStudy, JobCategory, Skill
from app.models.empresa import Company


class CatalogoService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def listar_carreras(self) -> list[CarreraResponse]:
        registros = self.db.scalars(select(FieldOfStudy).order_by(FieldOfStudy.name)).all()
        return [
            CarreraResponse(id=r.id, nombre=r.name, facultad=r.category)
            for r in registros
        ]

    def listar_habilidades(self) -> list[HabilidadResponse]:
        registros = self.db.scalars(
            select(Skill).where(Skill.is_active.is_(True)).order_by(Skill.name)
        ).all()
        return [HabilidadResponse(id=r.id, nombre=r.name) for r in registros]

    def listar_categorias(self) -> list[CategoriaOfertaResponse]:
        registros = self.db.scalars(
            select(JobCategory).where(JobCategory.is_active.is_(True)).order_by(JobCategory.name)
        ).all()
        return [CategoriaOfertaResponse(id=r.id, nombre=r.name) for r in registros]

    def listar_ciudades(self) -> list[CiudadResponse]:
        stmt = select(distinct(CandidateProfile.city)).where(CandidateProfile.city.is_not(None))
        stmt = stmt.union(
            select(distinct(Company.city)).where(Company.city.is_not(None))
        )
        nombres = sorted({nombre.strip() for (nombre,) in self.db.execute(stmt).all() if nombre and nombre.strip()})
        return [CiudadResponse(id=None, nombre=nombre) for nombre in nombres]
