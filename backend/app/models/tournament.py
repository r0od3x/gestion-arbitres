from __future__ import annotations

import uuid
from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Integer, String, Text, Time, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TournamentStatus

if TYPE_CHECKING:
    from app.models.assignment import TournamentAssignment


class Tournament(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tournaments"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="dates_coherentes"),
        CheckConstraint(
            "referees_needed IS NULL OR referees_needed > 0", name="referees_needed_positif"
        ),
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    venue: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    #: Heure à laquelle les arbitres doivent être présents.
    convocation_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    referees_needed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[TournamentStatus] = mapped_column(
        Enum(TournamentStatus, name="tournament_status", native_enum=False, length=20),
        default=TournamentStatus.DRAFT,
        nullable=False,
        index=True,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    assignments: Mapped[list[TournamentAssignment]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )
