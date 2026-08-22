from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import EstadoPostulacion


class Postulacion(Base):
    """Candidatura de un egresado a una vacante. Módulos 5.1.5 y 5.1.6."""

    __tablename__ = "postulaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    perfil_egresado_id: Mapped[int] = mapped_column(ForeignKey("perfiles_egresado.id"), nullable=False)
    oferta_id: Mapped[int] = mapped_column(ForeignKey("ofertas.id"), nullable=False)

    estado: Mapped[EstadoPostulacion] = mapped_column(
        Enum(EstadoPostulacion, name="estado_postulacion"), default=EstadoPostulacion.POSTULADO
    )
    comentario_egresado: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones_reclutador: Mapped[str | None] = mapped_column(Text, nullable=True)

    fecha_postulacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion_estado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RespuestaFiltro(Base):
    """Respuesta del postulante a una pregunta de filtro de la oferta."""

    __tablename__ = "respuestas_filtro"

    id: Mapped[int] = mapped_column(primary_key=True)
    postulacion_id: Mapped[int] = mapped_column(ForeignKey("postulaciones.id"), nullable=False)
    pregunta_filtro_id: Mapped[int] = mapped_column(ForeignKey("preguntas_filtro.id"), nullable=False)
    respuesta: Mapped[str] = mapped_column(String(255), nullable=False)


class EtapaSeleccion(Base):
    """Etapa configurable del proceso de selección de una vacante (HU-17)."""

    __tablename__ = "etapas_seleccion"

    id: Mapped[int] = mapped_column(primary_key=True)
    oferta_id: Mapped[int] = mapped_column(ForeignKey("ofertas.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    orden: Mapped[int] = mapped_column(nullable=False)


class PostulacionEtapa(Base):
    """Historial de avance de una postulación por las etapas del proceso."""

    __tablename__ = "postulacion_etapas"

    id: Mapped[int] = mapped_column(primary_key=True)
    postulacion_id: Mapped[int] = mapped_column(ForeignKey("postulaciones.id"), nullable=False)
    etapa_id: Mapped[int] = mapped_column(ForeignKey("etapas_seleccion.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
