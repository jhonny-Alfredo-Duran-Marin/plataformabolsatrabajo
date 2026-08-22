from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import EstadoValidacionEgresado


class PerfilEgresado(Base):
    """Perfil profesional del egresado. Módulos 5.1.2 (validación) y 5.1.3 (perfil y currículum)."""

    __tablename__ = "perfiles_egresado"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), unique=True, nullable=False)

    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    ci: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)

    carrera_id: Mapped[int | None] = mapped_column(ForeignKey("carreras.id"), nullable=True)
    anio_egreso: Mapped[int | None] = mapped_column(nullable=True)
    matricula: Mapped[str | None] = mapped_column(String(30), nullable=True)

    estado_laboral: Mapped[str | None] = mapped_column(String(30), nullable=True)
    estado_validacion: Mapped[EstadoValidacionEgresado] = mapped_column(
        Enum(EstadoValidacionEgresado, name="estado_validacion_egresado"),
        default=EstadoValidacionEgresado.PENDIENTE,
    )
    motivo_rechazo: Mapped[str | None] = mapped_column(Text, nullable=True)

    url_redes_profesionales: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cv_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    disponibilidad: Mapped[str | None] = mapped_column(String(50), nullable=True)

    perfil_oculto: Mapped[bool] = mapped_column(default=False)
    visibilidad_secciones: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON serializado
    porcentaje_completitud: Mapped[int] = mapped_column(default=0)

    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ExperienciaLaboral(Base):
    __tablename__ = "experiencias_laborales"

    id: Mapped[int] = mapped_column(primary_key=True)
    perfil_id: Mapped[int] = mapped_column(ForeignKey("perfiles_egresado.id"), nullable=False)
    empresa_nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    cargo: Mapped[str] = mapped_column(String(150), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    funciones: Mapped[str | None] = mapped_column(Text, nullable=True)


class FormacionAdicional(Base):
    __tablename__ = "formaciones_adicionales"

    id: Mapped[int] = mapped_column(primary_key=True)
    perfil_id: Mapped[int] = mapped_column(ForeignKey("perfiles_egresado.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)  # posgrado, diplomado, curso
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    institucion: Mapped[str | None] = mapped_column(String(150), nullable=True)
    anio: Mapped[int | None] = mapped_column(nullable=True)


class IdiomaEgresado(Base):
    __tablename__ = "idiomas_egresado"

    id: Mapped[int] = mapped_column(primary_key=True)
    perfil_id: Mapped[int] = mapped_column(ForeignKey("perfiles_egresado.id"), nullable=False)
    idioma: Mapped[str] = mapped_column(String(50), nullable=False)
    nivel: Mapped[str] = mapped_column(String(30), nullable=False)


class CertificacionEgresado(Base):
    __tablename__ = "certificaciones_egresado"

    id: Mapped[int] = mapped_column(primary_key=True)
    perfil_id: Mapped[int] = mapped_column(ForeignKey("perfiles_egresado.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    entidad_emisora: Mapped[str | None] = mapped_column(String(150), nullable=True)
    anio: Mapped[int | None] = mapped_column(nullable=True)


class HabilidadEgresado(Base):
    __tablename__ = "habilidades_egresado"

    id: Mapped[int] = mapped_column(primary_key=True)
    perfil_id: Mapped[int] = mapped_column(ForeignKey("perfiles_egresado.id"), nullable=False)
    habilidad_id: Mapped[int] = mapped_column(ForeignKey("habilidades.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), default="TECNICA")  # TECNICA | BLANDA
