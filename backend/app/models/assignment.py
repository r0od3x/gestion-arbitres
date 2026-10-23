from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AssignmentStatus

if TYPE_CHECKING:
    from app.models.notification import Notification
    from app.models.referee import RefereeProfile
    from app.models.tournament import Tournament


class TournamentAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Convocation d'un arbitre à un tournoi."""

    __tablename__ = "tournament_assignments"
    __table_args__ = (
        UniqueConstraint("tournament_id", "referee_id", name="uq_assignment_tournoi_arbitre"),
    )

    tournament_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referee_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role_in_tournament: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, name="assignment_status", native_enum=False, length=20),
        default=AssignmentStatus.PENDING,
        nullable=False,
        index=True,
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    tournament: Mapped[Tournament] = relationship(back_populates="assignments")
    referee: Mapped[RefereeProfile] = relationship(back_populates="assignments")
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )
