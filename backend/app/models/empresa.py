import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Sector(Base):
    """Catálogo de sectores económicos (tabla sector)."""

    __tablename__ = "sector"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)


class Company(Base):
    """Empresa registrada en la plataforma (tabla company del esquema real de Supabase).

    NOTA: el esquema real NO tiene legal_representative, rejection_reason,
    notifications_enabled, applications_enabled ni deleted_at. El motivo de
    rechazo/suspensión se guarda en la tabla company_verification (ver CompanyVerification
    más abajo); notifications_enabled/applications_enabled no tienen dónde persistirse
    (ver limitación documentada en empresa/service.py); "baja lógica" se modela
    reutilizando account_status='suspended' porque no existe una bandera de borrado separada.
    """

    __tablename__ = "company"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    legal_name: Mapped[str] = mapped_column(String(250), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tax_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    sector_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sector.id", ondelete="RESTRICT"), nullable=True
    )
    company_size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    account_status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sector: Mapped[Sector | None] = relationship()


class CompanyVerification(Base):
    """Historial de revisiones de verificación/autorización de una empresa (tabla company_verification).

    Aquí vive el motivo de rechazo/suspensión real (rejection_reason), ya que la tabla
    company no tiene esa columna directamente.
    """

    __tablename__ = "company_verification"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="in_review")
    document_key: Mapped[str] = mapped_column(String(500), nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CompanyMember(Base):
    """Usuario vinculado a una empresa con un rol dentro de ella (owner/admin/recruiter/viewer)."""

    __tablename__ = "company_member"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False
    )
    member_type: Mapped[str] = mapped_column(String(40), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
