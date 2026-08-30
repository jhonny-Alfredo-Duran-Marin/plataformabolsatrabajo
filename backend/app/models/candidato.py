import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CandidateProfile(Base):
    """Perfil del candidato / egresado (tabla candidate_profile del esquema real de Supabase).

    NOTA: carrera/año de egreso/matrícula no tienen columna propia; se guardan como una fila
    de CandidateEducation "principal" (con field_of_study_id set, ver app/features/perfil/service.py).
    `availability` y `section_visibility` se agregaron a la tabla real vía migración aditiva
    para cubrir HU-07 y HU-09 completos.
    """

    __tablename__ = "candidate_profile"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    professional_headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    professional_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_photo_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    document_country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    profile_visibility: Mapped[str] = mapped_column(String(30), nullable=False, default="platform")
    contact_visibility: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    job_search_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    availability: Mapped[str | None] = mapped_column(String(30), nullable=True)
    section_visibility: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {
            "experiencia_laboral": True,
            "formacion_adicional": True,
            "idiomas": True,
            "certificaciones": True,
            "habilidades": True,
        },
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CandidateEducation(Base):
    """Formación académica del candidato (tabla candidate_education)."""

    __tablename__ = "candidate_education"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False
    )
    # FK real hacia educational_institution(id) en la base de datos, pero esa tabla no
    # está mapeada en este backend (no se usa aún); se declara sin ForeignKey() de SQLAlchemy
    # para no romper la resolución de dependencias del ORM. La constraint sigue existiendo
    # y siendo validada por Postgres; este campo se deja siempre en None desde el código.
    institution_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    field_of_study_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("field_of_study.id", ondelete="SET NULL"), nullable=True
    )
    institution_name: Mapped[str | None] = mapped_column(String(250), nullable=True)
    program_name: Mapped[str] = mapped_column(String(250), nullable=False)
    education_level: Mapped[str] = mapped_column(String(40), nullable=False, default="undergraduate")
    academic_status: Mapped[str] = mapped_column(String(30), nullable=False, default="in_progress")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    graduation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkExperience(Base):
    """Experiencia laboral del candidato (tabla work_experience)."""

    __tablename__ = "work_experience"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company.id", ondelete="SET NULL"), nullable=True
    )
    company_name: Mapped[str | None] = mapped_column(String(250), nullable=True)
    position_title: Mapped[str] = mapped_column(String(200), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(40), nullable=False, default="full_time")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currently_working: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    salary_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CandidateLanguage(Base):
    """Idiomas declarados por el candidato (tabla candidate_language, PK compuesta)."""

    __tablename__ = "candidate_language"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profile.id", ondelete="CASCADE"), primary_key=True
    )
    language_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("language.id", ondelete="RESTRICT"), primary_key=True
    )
    proficiency_level: Mapped[str] = mapped_column(String(30), nullable=False, default="basic")


class Certification(Base):
    """Certificaciones obtenidas por el candidato (tabla certification)."""

    __tablename__ = "certification"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(250), nullable=True)
    credential_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    credential_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CandidateSkill(Base):
    """Relación N:M entre candidatos y el catálogo de habilidades (tabla candidate_skill)."""

    __tablename__ = "candidate_skill"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profile.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skill.id", ondelete="RESTRICT"), primary_key=True
    )
    proficiency_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    years_experience: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
