from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RefereeGrade

if TYPE_CHECKING:
    from app.models.assignment import TournamentAssignment
    from app.models.user import User


class RefereeProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "referee_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    #: Format E.164, ex. +2126XXXXXXXX
    phone_e164: Mapped[str | None] = mapped_column(
        String(20), unique=True, index=True, nullable=True
    )

    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    whatsapp_opt_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    grade: Mapped[RefereeGrade] = mapped_column(
        Enum(RefereeGrade, name="referee_grade", native_enum=False, length=20),
        default=RefereeGrade.REGIONAL,
        nullable=False,
        index=True,
    )
    license_number: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    club: Mapped[str | None] = mapped_column(String(150), nullable=True)
    league: Mapped[str | None] = mapped_column(String(150), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    #: Visible uniquement par les administrateurs.
    notes_admin: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="referee_profile", lazy="joined")
    assignments: Mapped[list[TournamentAssignment]] = relationship(
        back_populates="referee", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_notifiable(self) -> bool:
        """Peut recevoir une convocation WhatsApp : consentement + numéro valide."""
        return bool(self.whatsapp_opt_in and self.phone_e164)
