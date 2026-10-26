import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Survey(Base):
    """Encuesta de situación laboral que la universidad envía a sus egresados (tabla survey) — HU-30.

    El diseño original no tenía el período; se agregó `period` porque el egresado responde una
    encuesta por período y el administrador mide el avance de cada uno.
    """

    __tablename__ = "survey"
    __table_args__ = (
        CheckConstraint("target_scope IN ('all_candidates', 'institution', 'field_of_study')", name="ck_survey_scope"),
        CheckConstraint(
            "(target_scope <> 'all_candidates') OR (institution_id IS NULL AND field_of_study_id IS NULL)",
            name="ck_survey_scope_all",
        ),
        CheckConstraint(
            "(target_scope <> 'institution') OR (institution_id IS NOT NULL)", name="ck_survey_scope_institution"
        ),
        CheckConstraint(
            "(target_scope <> 'field_of_study') OR (field_of_study_id IS NOT NULL)", name="ck_survey_scope_field"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    period: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    # all_candidates (solo el superadmin), institution (toda la universidad) o field_of_study (una carrera)
    target_scope: Mapped[str] = mapped_column(String(30), nullable=False, default="institution")
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("educational_institution.id", ondelete="SET NULL"), nullable=True
    )
    field_of_study_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("field_of_study.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    questions = relationship(
        "SurveyQuestion", back_populates="survey", cascade="all, delete-orphan", order_by="SurveyQuestion.position"
    )
    field_of_study = relationship("FieldOfStudy")


class SurveyQuestion(Base):
    __tablename__ = "survey_question"
    __table_args__ = (
        UniqueConstraint("survey_id", "position", name="uq_survey_question_position"),
        CheckConstraint("question_type IN ('single_choice', 'text', 'number', 'scale')", name="ck_survey_question_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Clave estable de la pregunta (situacion_laboral, empresa...): el tablero de indicadores
    # (HU-31) lee las respuestas por este código y no por el texto, que puede cambiar.
    code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    survey = relationship("Survey", back_populates="questions")
    options = relationship(
        "SurveyQuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="SurveyQuestionOption.position",
    )


class SurveyQuestionOption(Base):
    __tablename__ = "survey_question_option"
    __table_args__ = (UniqueConstraint("question_id", "position", name="uq_survey_option_position"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_question.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    option_text: Mapped[str] = mapped_column(String(300), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    question = relationship("SurveyQuestion", back_populates="options")


class SurveyResponse(Base):
    """Respuesta de un egresado a una encuesta: una sola por egresado y encuesta."""

    __tablename__ = "survey_response"
    __table_args__ = (UniqueConstraint("survey_id", "candidate_id", name="uq_survey_response_candidate"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    survey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_profile.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    answers = relationship("SurveyAnswer", back_populates="response", cascade="all, delete-orphan")


class SurveyAnswer(Base):
    __tablename__ = "survey_answer"
    __table_args__ = (UniqueConstraint("response_id", "question_id", name="uq_survey_answer_question"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_response.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_question.id", ondelete="RESTRICT"), nullable=False
    )
    selected_option_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("survey_question_option.id", ondelete="SET NULL"), nullable=True
    )
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_number: Mapped[Decimal | None] = mapped_column(Numeric(15, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    response = relationship("SurveyResponse", back_populates="answers")
