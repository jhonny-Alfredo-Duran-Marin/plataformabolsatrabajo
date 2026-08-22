from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Mensaje(Base):
    """Mensajería interna entre empresa y candidato. Módulo 5.1.7."""

    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(primary_key=True)
    remitente_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    destinatario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    asunto: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_envio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    leido: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_lectura: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Entrevista(Base):
    """Entrevista agendada dentro de una postulación. Módulo 5.1.7."""

    __tablename__ = "entrevistas"

    id: Mapped[int] = mapped_column(primary_key=True)
    postulacion_id: Mapped[int] = mapped_column(ForeignKey("postulaciones.id"), nullable=False)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modalidad: Mapped[str] = mapped_column(String(30), nullable=False)
    confirmada: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
