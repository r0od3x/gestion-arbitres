from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import joinedload, selectinload

from app.models.assignment import TournamentAssignment
from app.models.enums import AssignmentStatus
from app.models.referee import RefereeProfile
from app.models.tournament import Tournament
from app.repositories.base import BaseRepository


class AssignmentRepository(BaseRepository[TournamentAssignment]):
    model = TournamentAssignment

    async def get_with_relations(self, assignment_id: uuid.UUID) -> TournamentAssignment | None:
        statement = (
            select(TournamentAssignment)
            .where(TournamentAssignment.id == assignment_id)
            .options(
                joinedload(TournamentAssignment.tournament),
                joinedload(TournamentAssignment.referee).joinedload(RefereeProfile.user),
                selectinload(TournamentAssignment.notifications),
            )
        )
        return await self.session.scalar(statement)

    async def list_for_tournament(
        self, tournament_id: uuid.UUID, *, include_cancelled: bool = False
    ) -> list[TournamentAssignment]:
        statement = (
            select(TournamentAssignment)
            .where(TournamentAssignment.tournament_id == tournament_id)
            .options(
                joinedload(TournamentAssignment.referee).joinedload(RefereeProfile.user),
                selectinload(TournamentAssignment.notifications),
            )
            .join(TournamentAssignment.referee)
            .order_by(RefereeProfile.last_name, RefereeProfile.first_name)
        )
        if not include_cancelled:
            statement = statement.where(TournamentAssignment.status != AssignmentStatus.CANCELLED)
        return list((await self.session.scalars(statement)).unique())

    def for_referee_statement(
        self, referee_id: uuid.UUID, *, upcoming: bool | None = None
    ) -> Select[TournamentAssignment]:
        """Convocations d'un arbitre, les annulées exclues."""
        statement = (
            select(TournamentAssignment)
            .where(
                TournamentAssignment.referee_id == referee_id,
                TournamentAssignment.status != AssignmentStatus.CANCELLED,
            )
            .join(TournamentAssignment.tournament)
            .options(joinedload(TournamentAssignment.tournament))
        )
        if upcoming is not None:
            today = date.today()
            statement = statement.where(
                Tournament.end_date >= today if upcoming else Tournament.end_date < today
            )
        return statement

    async def list_for_referee(
        self, referee_id: uuid.UUID, *, upcoming: bool | None = None
    ) -> list[TournamentAssignment]:
        statement = self.for_referee_statement(referee_id, upcoming=upcoming).order_by(
            Tournament.start_date.desc()
        )
        return list((await self.session.scalars(statement)).unique())

    async def get_by_tournament_and_referee(
        self, tournament_id: uuid.UUID, referee_id: uuid.UUID
    ) -> TournamentAssignment | None:
        statement = select(TournamentAssignment).where(
            TournamentAssignment.tournament_id == tournament_id,
            TournamentAssignment.referee_id == referee_id,
        )
        return await self.session.scalar(statement)
