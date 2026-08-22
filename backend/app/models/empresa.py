from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import EstadoVerificacionEmpresa


class Empresa(Base):
    """Empresa / reclutador. Módulo 5.1.2 — validación institucional de empresas."""

    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), unique=True, nullable=False)

    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    nit: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    tamanio: Mapped[str | None] = mapped_column(String(50), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sitio_web: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    representante_legal: Mapped[str | None] = mapped_column(String(150), nullable=True)

    estado_verificacion: Mapped[EstadoVerificacionEmpresa] = mapped_column(
        Enum(EstadoVerificacionEmpresa, name="estado_verificacion_empresa"),
        default=EstadoVerificacionEmpresa.PENDIENTE,
    )
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)

    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
