import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Application(Base):
    """Postulación de un candidato a una vacante (tabla application)."""

    __tablename__ = "application"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidate_profile.id"), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_posting.id"), nullable=False)
    submitted_cv_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    current_stage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_selection_stage.id", ondelete="SET NULL"), nullable=True
    )
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_status: Mapped[str] = mapped_column(String(30), nullable=False, default="applied")
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relaciones ORM — HU-14 (postulación), HU-15 (seguimiento), HU-17 (selección)
    candidate = relationship("CandidateProfile", backref="applications")
    job_posting = relationship("JobPosting", backref="applications")
    current_stage = relationship("JobSelectionStage")
    answers: Mapped[list["ApplicationAnswer"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    status_history: Mapped[list["ApplicationStatusHistory"]] = relationship(
        back_populates="application",
        order_by="ApplicationStatusHistory.created_at.desc()",
        cascade="all, delete-orphan",
    )
    stage_history: Mapped[list["ApplicationStageHistory"]] = relationship(
        back_populates="application",
        order_by="ApplicationStageHistory.entered_at.asc()",
        cascade="all, delete-orphan",
    )
    notes: Mapped[list["ApplicationNote"]] = relationship(
        back_populates="application",
        order_by="ApplicationNote.created_at.desc()",
        cascade="all, delete-orphan",
    )


class ApplicationAnswer(Base):
    """Respuesta del candidato a una pregunta de filtro de la vacante (tabla application_answer)."""

    __tablename__ = "application_answer"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("application.id"), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("screening_question.id"), nullable=False)
    selected_option_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("screening_option.id"), nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_number: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApplicationStatusHistory(Base):
    """Historial de cambios de estado de una postulación (tabla application_status_history) — HU-15."""

    __tablename__ = "application_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application = relationship("Application", back_populates="status_history")
    author = relationship("AppUser")


class ApplicationStageHistory(Base):
    """Historial de auditoría de avances y descartes de cada postulante (tabla application_stage_history) — HU-17."""

    __tablename__ = "application_stage_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application.id", ondelete="CASCADE"), nullable=False
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_selection_stage.id", ondelete="RESTRICT"), nullable=False
    )
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    result: Mapped[str | None] = mapped_column(String(20), nullable=True)  # passed | failed | pending
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    application = relationship("Application", back_populates="stage_history")
    stage = relationship("JobSelectionStage")


class ApplicationNote(Base):
    """Observación interna del equipo de la empresa sobre un postulante (tabla application_note) — HU-17."""

    __tablename__ = "application_note"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application.id", ondelete="CASCADE"), nullable=False
    )
    company_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_member.id", ondelete="RESTRICT"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    application = relationship("Application", back_populates="notes")
    member = relationship("CompanyMember")
