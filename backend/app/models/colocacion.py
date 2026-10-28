import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Placement(Base):
    """Contratación de un egresado que la universidad registra (tabla placement) — HU-29.

    Adaptación del diseño V3: `application_id` es opcional (hay colocaciones que no pasaron por la
    plataforma), se agrega `institution_id` para el multitenant y el borrado es lógico. La empresa es
    una empresa registrada (`company_id`) o, si no lo está, un nombre libre (`company_name`).
    """

    __tablename__ = "placement"
    __table_args__ = (
        CheckConstraint("status IN ('suggested', 'confirmed', 'cancelled')", name="ck_placement_status"),
        CheckConstraint("source IN ('platform', 'manual')", name="ck_placement_source"),
        CheckConstraint("company_id IS NOT NULL OR company_name IS NOT NULL", name="ck_placement_company"),
        CheckConstraint("salary_amount IS NULL OR salary_amount >= 0", name="ck_placement_salary"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Único cuando existe: una postulación genera a lo sumo una colocación (los NULL no chocan entre sí).
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application.id", ondelete="RESTRICT"), unique=True, nullable=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profile.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("educational_institution.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company.id", ondelete="RESTRICT"), nullable=True
    )
    company_name: Mapped[str | None] = mapped_column(String(250), nullable=True)
    position_title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    # La columna conserva el nombre del diseño V3 (la tabla ya existe en Supabase).
    salary: Mapped[Decimal | None] = mapped_column("salary_amount", Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    # suggested (la plataforma la propone), confirmed (la universidad la validó) o cancelled (eliminada).
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    # Motivo del último cambio hecho a mano (el detalle de cada cambio va a la bitácora).
    updated_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    candidate = relationship("CandidateProfile")
    company = relationship("Company")
    institution = relationship("Institution")
