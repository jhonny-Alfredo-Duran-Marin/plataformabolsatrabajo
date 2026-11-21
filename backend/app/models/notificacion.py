import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Notification(Base):
    """Notificación enviada a un usuario del sistema (tabla notification) — HU-17, HU-21."""

    __tablename__ = "notification"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("AppUser")


class NotificationPreference(Base):
    """Preferencias de notificación de un usuario (tabla notification_preference) — HU-21."""

    __tablename__ = "notification_preference"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        primary_key=True,
    )
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_stage_changes: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_job_matches: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_interview_events: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_messages: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("AppUser")


class UserDeviceToken(Base):
    """Tokens de dispositivos registrados para notificaciones Push Firebase (FCM) — HU-21."""

    __tablename__ = "user_device_token"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fcm_token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    device_type: Mapped[str] = mapped_column(String(20), nullable=False, default="web")  # web, android, ios
    device_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("AppUser")


class PushPending(Base):
    """Push que falló por un error pasajero de Firebase y espera su reintento (tabla push_pendiente) — HU-36.

    `tokens` guarda solo los dispositivos que fallaron, así el reintento no duplica el aviso en los que
    ya lo recibieron. `intentos` cuenta el envío original (1) más los reintentos (máximo 4 en total).
    """

    __tablename__ = "push_pendiente"
    __table_args__ = (CheckConstraint("estado IN ('pendiente', 'enviado', 'fallido')", name="ck_push_pendiente_estado"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    cuerpo: Mapped[str | None] = mapped_column(Text, nullable=True)
    enlace: Mapped[str | None] = mapped_column(String(500), nullable=True)
    datos: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tokens: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    ultimo_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    proximo_intento_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("AppUser")
