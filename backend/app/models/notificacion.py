from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import TipoNotificacion


class Notificacion(Base):
    """Notificación centralizada por correo/push. Módulo 5.1.8."""

    __tablename__ = "notificaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    tipo: Mapped[TipoNotificacion] = mapped_column(Enum(TipoNotificacion, name="tipo_notificacion"), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    enlace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    leido: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_lectura: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
