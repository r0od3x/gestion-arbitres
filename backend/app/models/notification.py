from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import NotificationChannel, NotificationStatus, NotificationType

if TYPE_CHECKING:
    from app.models.assignment import TournamentAssignment

#: JSONB sur Postgres, JSON ailleurs (SQLite en dev/tests).
JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Une tentative d'envoi de message vers un arbitre, suivie jusqu'à sa livraison."""

    __tablename__ = "notifications"

    #: Nullable : permet des messages génériques non liés à une convocation.
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tournament_assignments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    recipient_phone_e164: Mapped[str] = mapped_column(String(20), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel", native_enum=False, length=20),
        default=NotificationChannel.WHATSAPP,
        nullable=False,
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", native_enum=False, length=20),
        nullable=False,
    )
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    #: Variables du template ({{1}}, {{2}}, …) et métadonnées d'envoi.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)

    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status", native_enum=False, length=20),
        default=NotificationStatus.QUEUED,
        nullable=False,
        index=True,
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assignment: Mapped[TournamentAssignment | None] = relationship(back_populates="notifications")
