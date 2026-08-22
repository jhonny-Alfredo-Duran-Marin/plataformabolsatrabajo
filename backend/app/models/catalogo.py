from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Carrera(Base):
    """Catálogo de carreras de la UAGRM (módulo 5.1.2 / 5.1.10)."""

    __tablename__ = "carreras"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    facultad: Mapped[str | None] = mapped_column(String(150), nullable=True)


class Habilidad(Base):
    """Catálogo de habilidades predefinidas (módulo 6.1.9)."""

    __tablename__ = "habilidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    aprobada: Mapped[bool] = mapped_column(default=True)


class CategoriaOferta(Base):
    """Áreas laborales para clasificar vacantes (módulo 6.1.9)."""

    __tablename__ = "categorias_oferta"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Ciudad(Base):
    __tablename__ = "ciudades"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
