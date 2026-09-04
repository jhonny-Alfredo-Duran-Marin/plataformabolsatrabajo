import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.candidato import CandidateProfile
from app.models.oferta import JobPosting
from app.models.usuario import AppUser


class JobSelectionStage(Base):
    """Etapas configuradas para el proceso de selección de una vacante (tabla job_selection_stage)."""

    __tablename__ = "job_selection_stage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_posting.id", ondelete="CASCADE"), nullable=False
    )
    stage_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job_posting: Mapped[JobPosting] = relationship(lazy="joined")


class Application(Base):
    """Postulación de un candidato a una oferta de empleo (tabla application)."""

    __tablename__ = "application"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_posting.id", ondelete="CASCADE"), nullable=False
    )
    submitted_cv_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    current_stage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_selection_stage.id", ondelete="SET NULL"), nullable=True
    )
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="applied"
    )  # applied | in_review | shortlisted | interview | offered | hired | rejected | withdrawn
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate: Mapped[CandidateProfile] = relationship(lazy="joined")
    job_posting: Mapped[JobPosting] = relationship(lazy="joined")
    current_stage: Mapped[JobSelectionStage | None] = relationship(lazy="joined")
    stage_history: Mapped[list["ApplicationStageHistory"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ApplicationStageHistory.entered_at"
    )
    notes: Mapped[list["ApplicationNote"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ApplicationNote.created_at.desc()"
    )


class ApplicationStageHistory(Base):
    """Historial de auditoría de avances y descartes de cada postulante (tabla application_stage_history)."""

    __tablename__ = "application_stage_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application.id", ondelete="CASCADE"), nullable=False
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_selection_stage.id", ondelete="CASCADE"), nullable=False
    )
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    result: Mapped[str | None] = mapped_column(String(20), nullable=True)  # passed | rejected | pending
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    stage: Mapped[JobSelectionStage] = relationship(lazy="joined")
    changed_by_user: Mapped[AppUser | None] = relationship(lazy="joined")


class ApplicationNote(Base):
    """Observaciones internas del equipo de selección (tabla application_note)."""

    __tablename__ = "application_note"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application.id", ondelete="CASCADE"), nullable=False
    )
    company_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    author: Mapped[AppUser] = relationship(lazy="joined")


class Notification(Base):
    """Notificaciones enviadas a los usuarios del sistema (tabla notification)."""

    __tablename__ = "notification"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)  # stage_change | application_status
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

