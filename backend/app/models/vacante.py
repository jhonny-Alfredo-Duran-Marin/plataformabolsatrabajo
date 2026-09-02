import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.catalogo import JobCategory, Skill
    from app.models.empresa import Company
    from app.models.usuario import AppUser


# ─── Enumeraciones del Dominio de Vacantes ───────────────────────────────────
# Los valores coinciden exactamente con los CHECK constraints de la Supabase
# real (tabla job_posting / job_skill), no con el diseño lógico V3 original.


class SeniorityLevel(str, enum.Enum):
    """Nivel de experiencia requerido para la vacante (ck_job_seniority)."""

    INTERNSHIP = "internship"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"


class EmploymentType(str, enum.Enum):
    """Tipo de contrato o relación laboral (ck_job_emp_type)."""

    PERMANENT = "permanent"
    TEMPORARY = "temporary"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    PART_TIME = "part_time"
    FREELANCE = "freelance"


class WorkModality(str, enum.Enum):
    """Modalidad de trabajo (ck_job_modality)."""

    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"


class JobStatus(str, enum.Enum):
    """Estado del ciclo de vida de una vacante.

    draft/published/paused/closed/archived vienen del ck_job_status original;
    pending_review y rejected se agregaron con la migración de HU-12
    (moderación de ofertas) — ver ALTER de ck_job_status en Supabase.
    """

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    PAUSED = "paused"
    CLOSED = "closed"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class SkillProficiencyLevel(str, enum.Enum):
    """Nivel de dominio de habilidad requerido (ck_js_proficiency)."""

    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class SkillImportance(str, enum.Enum):
    """Qué tan determinante es una habilidad para la vacante (ck_js_importance)."""

    REQUIRED = "required"
    PREFERRED = "preferred"
    OPTIONAL = "optional"


# ─── Modelo Principal: JobPosting ───────────────────────────────────────────


class JobPosting(Base):
    """Oferta laboral o vacante publicada por una empresa (tabla job_posting real de Supabase)."""

    __tablename__ = "job_posting"

    # Identificación y Relaciones Principales
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_category.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )

    # Información Básica
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    requirements_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    benefits_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Condiciones y Modalidad (NOT NULL en la BD real)
    seniority_level: Mapped[str] = mapped_column(String(30), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    work_modality: Mapped[str] = mapped_column(String(20), nullable=False, default=WorkModality.ONSITE.value)
    min_education_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    min_years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Ubicación
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="BO")
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    # Rango Salarial
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True, default="BOB")
    salary_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Posiciones, Estado del Ciclo de Vida y Moderación
    positions_available: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=JobStatus.DRAFT.value, index=True)
    rejection_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Motivo indicado por el moderador al rechazar la vacante (HU-12)."
    )
    application_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Trazabilidad Temporal
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones ORM
    company: Mapped["Company"] = relationship()
    category: Mapped["JobCategory | None"] = relationship()
    creador: Mapped["AppUser | None"] = relationship()
    skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<JobPosting(id={self.id}, title='{self.title}', status='{self.status}', company_id={self.company_id})>"


# ─── Modelo Secundario / Satélite: JobSkill ─────────────────────────────────


class JobSkill(Base):
    """Habilidad técnica o blanda requerida para una vacante (tabla job_skill)."""

    __tablename__ = "job_skill"
    __table_args__ = (
        CheckConstraint("(weight IS NULL) OR (weight >= 0 AND weight <= 100)", name="ck_job_skill_weight_range_orm"),
    )

    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_posting.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skill.id", ondelete="RESTRICT"), primary_key=True
    )
    importance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    min_proficiency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relaciones ORM
    job: Mapped["JobPosting"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship()

    def __repr__(self) -> str:
        return f"<JobSkill(job_posting_id={self.job_posting_id}, skill_id={self.skill_id}, importance={self.importance})>"
