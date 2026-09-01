import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.catalogo import JobCategory, Skill
    from app.models.empresa import Company, CompanyMember


# ─── Enumeraciones del Dominio de Vacantes ───────────────────────────────────


class SeniorityLevel(str, enum.Enum):
    """Nivel de experiencia requerido para la vacante."""

    INTERNSHIP = "internship"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"


class EmploymentType(str, enum.Enum):
    """Tipo de contrato o relación laboral."""

    PERMANENT = "permanent"
    TEMPORARY = "temporary"
    PROJECT = "project"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"


class WorkModality(str, enum.Enum):
    """Modalidad de trabajo."""

    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"


class JobStatus(str, enum.Enum):
    """Estado del ciclo de vida de una vacante."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    PAUSED = "paused"
    CLOSED = "closed"
    REJECTED = "rejected"


class SkillProficiencyLevel(str, enum.Enum):
    """Nivel de dominio de habilidad requerido."""

    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


# ─── Modelo Principal: JobPosting ───────────────────────────────────────────


class JobPosting(Base):
    """Oferta laboral o vacante publicada por una empresa (tabla job_posting).

    Diseñada según las especificaciones del Módulo 6 (Diseño Lógico V3).
    """

    __tablename__ = "job_posting"
    __table_args__ = (
        CheckConstraint("positions_count > 0", name="ck_job_posting_positions_count"),
        CheckConstraint(
            "(salary_min IS NULL) OR (salary_max IS NULL) OR (salary_min <= salary_max)",
            name="ck_job_posting_salary_range",
        ),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="ck_job_posting_coordinates_pair",
        ),
    )

    # Identificación y Relaciones Principales
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_by_member_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_member.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_category.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Información Básica
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Condiciones y Modalidad
    seniority_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    work_modality: Mapped[str | None] = mapped_column(String(20), nullable=True, default=WorkModality.ONSITE.value)
    minimum_education_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    required_experience_years: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True, default=0.0)

    # Ubicación (Geolocalización opcional)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True, default="BO")
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    # Rango Salarial
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True, default="BOB")
    salary_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Posiciones y Estado del Ciclo de Vida
    positions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default=JobStatus.DRAFT.value, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Trazabilidad Temporal
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relaciones ORM
    company: Mapped["Company"] = relationship()
    created_by_member: Mapped["CompanyMember | None"] = relationship()
    category: Mapped["JobCategory | None"] = relationship()
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
        UniqueConstraint("job_id", "skill_id", name="uq_job_skill_job_skill"),
        CheckConstraint(
            "(weight IS NULL) OR (weight >= 0 AND weight <= 100)",
            name="ck_job_skill_weight_range",
        ),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_posting.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skill.id", ondelete="RESTRICT"), primary_key=True
    )
    required_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Relaciones ORM
    job: Mapped["JobPosting"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship()

    def __repr__(self) -> str:
        return f"<JobSkill(job_id={self.job_id}, skill_id={self.skill_id}, is_required={self.is_required})>"
