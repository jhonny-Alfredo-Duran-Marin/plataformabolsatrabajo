from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BitacoraLog(Base):
    """Bitácora de operaciones críticas del sistema. Módulo 5.1.1 (RNF-18)."""

    __tablename__ = "bitacora_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    detalles: Mapped[str | None] = mapped_column(Text, nullable=True)
    resultado: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
