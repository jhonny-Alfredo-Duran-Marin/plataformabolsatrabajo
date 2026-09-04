import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class JobPosting(Base):
    __tablename__ = "job_posting"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("job_category.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    requirements_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    benefits_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    seniority_level: Mapped[str] = mapped_column(String(40), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(40), nullable=False)
    work_modality: Mapped[str] = mapped_column(String(20), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    salary_min: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    salary_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    positions_available: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    min_education_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    min_years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    application_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ScreeningQuestion(Base):
    __tablename__ = "screening_question"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_posting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_posting.id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_knockout: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    min_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ScreeningOption(Base):
    __tablename__ = "screening_option"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("screening_question.id"), nullable=False)
    option_text: Mapped[str] = mapped_column(String(300), nullable=False)
    is_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
