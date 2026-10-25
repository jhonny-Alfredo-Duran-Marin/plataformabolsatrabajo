import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChatbotSession(Base):
    """Sesión de conversación del usuario con el chatbot de orientación (HU-28, tabla chatbot_session)."""

    __tablename__ = "chatbot_session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("AppUser")
    messages: Mapped[list["ChatbotMessage"]] = relationship(
        "ChatbotMessage",
        back_populates="session",
        order_by="ChatbotMessage.created_at.asc()",
        cascade="all, delete-orphan",
    )


class ChatbotMessage(Base):
    """Mensaje individual registrado en una sesión del chatbot (HU-28, tabla chatbot_message)."""

    __tablename__ = "chatbot_message"
    __table_args__ = (
        CheckConstraint("message_role IN ('user', 'assistant', 'system')", name="ck_chatbot_message_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chatbot_session.id", ondelete="CASCADE"), nullable=False
    )
    message_role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("ChatbotSession", back_populates="messages")
