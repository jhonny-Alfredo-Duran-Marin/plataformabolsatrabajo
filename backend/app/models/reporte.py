from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReporteInstitucional(Base):
    """Reporte generado por el administrador universitario. Módulo 5.1.10."""

    __tablename__ = "reportes_institucionales"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    parametros_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    resultados_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    formato: Mapped[str] = mapped_column(String(10), default="PDF")
    usuario_generador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Colocacion(Base):
    """Contratación concretada, insumo de la tasa de colocación (HU-29)."""

    __tablename__ = "colocaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    perfil_egresado_id: Mapped[int] = mapped_column(ForeignKey("perfiles_egresado.id"), nullable=False)
    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id"), nullable=True)
    cargo: Mapped[str] = mapped_column(String(150), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    postulacion_id: Mapped[int | None] = mapped_column(ForeignKey("postulaciones.id"), nullable=True)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EncuestaSituacionLaboral(Base):
    """Encuesta periódica de seguimiento de egresados (HU-30)."""

    __tablename__ = "encuestas_situacion_laboral"

    id: Mapped[int] = mapped_column(primary_key=True)
    perfil_egresado_id: Mapped[int] = mapped_column(ForeignKey("perfiles_egresado.id"), nullable=False)
    fecha_envio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_respuesta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    respuesta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
