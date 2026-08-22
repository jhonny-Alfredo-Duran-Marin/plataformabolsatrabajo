from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import EstadoOferta, ModalidadTrabajo, NivelExperiencia, TipoContrato


class Oferta(Base):
    """Vacante publicada por una empresa. Módulo 5.1.4 — gestión de vacantes."""

    __tablename__ = "ofertas"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)

    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    requisitos: Mapped[str | None] = mapped_column(Text, nullable=True)
    beneficios: Mapped[str | None] = mapped_column(Text, nullable=True)

    ciudad_id: Mapped[int | None] = mapped_column(ForeignKey("ciudades.id"), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    modalidad: Mapped[ModalidadTrabajo] = mapped_column(Enum(ModalidadTrabajo, name="modalidad_trabajo"), nullable=False)
    tipo_contrato: Mapped[TipoContrato] = mapped_column(Enum(TipoContrato, name="tipo_contrato"), nullable=False)
    jornada: Mapped[str | None] = mapped_column(String(30), nullable=True)
    salario_min: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    salario_max: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias_oferta.id"), nullable=True)
    carrera_afin_id: Mapped[int | None] = mapped_column(ForeignKey("carreras.id"), nullable=True)
    nivel_experiencia: Mapped[NivelExperiencia | None] = mapped_column(
        Enum(NivelExperiencia, name="nivel_experiencia"), nullable=True
    )
    numero_vacantes: Mapped[int] = mapped_column(default=1)

    estado: Mapped[EstadoOferta] = mapped_column(Enum(EstadoOferta, name="estado_oferta"), default=EstadoOferta.EN_REVISION)
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)

    fecha_publicacion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PreguntaFiltro(Base):
    """Pregunta de respuesta cerrada que descarta postulantes (HU-11)."""

    __tablename__ = "preguntas_filtro"

    id: Mapped[int] = mapped_column(primary_key=True)
    oferta_id: Mapped[int] = mapped_column(ForeignKey("ofertas.id"), nullable=False)
    texto: Mapped[str] = mapped_column(String(255), nullable=False)
    respuesta_excluyente: Mapped[str] = mapped_column(String(100), nullable=False)
