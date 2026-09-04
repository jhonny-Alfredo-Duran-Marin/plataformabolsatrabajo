import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobPosting(Base):
    """Vacante publicada por una empresa (tabla job_posting del esquema PostgreSQL)."""

    __tablename__ = "job_posting"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_category.id", ondelete="RESTRICT"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    seniority_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    employment_type: Mapped[str] = mapped_column(String(30), nullable=False, default="permanent")
    work_modality: Mapped[str] = mapped_column(String(20), nullable=False, default="onsite")
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True, default="BOB")
    salary_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    positions_available: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published")
    min_education_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    min_years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    application_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", backref="job_postings")
    category = relationship("JobCategory")
    skills = relationship("JobSkill", back_populates="job_posting", cascade="all, delete-orphan")
    stages = relationship(
        "JobSelectionStage",
        back_populates="job_posting",
        order_by="JobSelectionStage.stage_number",
        cascade="all, delete-orphan",
    )


class JobSkill(Base):
    """Habilidades requeridas/preferidas en una vacante (tabla job_skill)."""

    __tablename__ = "job_skill"

    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_posting.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skill.id", ondelete="RESTRICT"), primary_key=True
    )
    importance: Mapped[str | None] = mapped_column(String(20), nullable=True, default="required")
    min_proficiency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)

    job_posting = relationship("JobPosting", back_populates="skills")
    skill = relationship("Skill")


class JobSelectionStage(Base):
    """Etapas del proceso de selección de una vacante (tabla job_selection_stage)."""

    __tablename__ = "job_selection_stage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_posting.id", ondelete="CASCADE"), nullable=False
    )
    stage_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job_posting = relationship("JobPosting", back_populates="stages")


class JobLanguageRequirement(Base):
    """Requisitos de idiomas para la vacante (tabla job_language_requirement)."""

    __tablename__ = "job_language_requirement"

    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_posting.id", ondelete="CASCADE"), primary_key=True
    )
    language_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("language.id", ondelete="RESTRICT"), primary_key=True
    )
    proficiency_level: Mapped[str] = mapped_column(String(30), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    language = relationship("Language")


class JobEducationPreference(Base):
    """Preferencia o requisito educativo para la vacante (tabla job_education_preference)."""

    __tablename__ = "job_education_preference"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_posting.id", ondelete="CASCADE"), nullable=False
    )
    field_of_study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("field_of_study.id", ondelete="RESTRICT"), nullable=False
    )
    education_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    field_of_study = relationship("FieldOfStudy")
