import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.catalogo import FieldOfStudy, JobCategory, Skill
from app.models.empresa import Company


class JobSkill(Base):
    """Habilidades requeridas o deseadas para una vacante (tabla job_skill)."""

    __tablename__ = "job_skill"

    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_posting.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skill.id", ondelete="CASCADE"), primary_key=True
    )
    importance: Mapped[str] = mapped_column(String(20), nullable=False, default="required")  # required | preferred
    min_proficiency: Mapped[str | None] = mapped_column(String(20), nullable=True)  # basic | intermediate | advanced
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)

    skill: Mapped[Skill] = relationship(lazy="joined")


class JobEducationPreference(Base):
    """Preferencias o requisitos de carrera y nivel de estudio (tabla job_education_preference)."""

    __tablename__ = "job_education_preference"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_posting.id", ondelete="CASCADE"), nullable=False
    )
    field_of_study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("field_of_study.id", ondelete="RESTRICT"), nullable=False
    )
    education_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    field_of_study: Mapped[FieldOfStudy] = relationship(lazy="joined")


class JobPosting(Base):
    """Oferta laboral o vacante publicada por una empresa (tabla job_posting)."""

    __tablename__ = "job_posting"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_category.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    requirements_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    benefits_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    seniority_level: Mapped[str] = mapped_column(String(40), nullable=False, default="junior")
    employment_type: Mapped[str] = mapped_column(String(40), nullable=False, default="full_time")
    work_modality: Mapped[str] = mapped_column(String(20), nullable=False, default="on_site")
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="BO")
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="Santa Cruz de la Sierra")
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True, default="BOB")
    salary_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    positions_available: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft | published | closed | paused
    min_education_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    min_years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    application_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    company: Mapped[Company] = relationship(lazy="joined")
    category: Mapped[JobCategory | None] = relationship(lazy="joined")
    skills: Mapped[list[JobSkill]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    education_preferences: Mapped[list[JobEducationPreference]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )

