from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Select, case, func, select

from app.models.assignment import TournamentAssignment
from app.models.enums import AssignmentStatus, TournamentStatus
from app.models.tournament import Tournament
from app.repositories.base import BaseRepository


class TournamentRepository(BaseRepository[Tournament]):
    model = Tournament

    def search_statement(
        self,
        *,
        status: TournamentStatus | None = None,
        city: str | None = None,
        upcoming: bool | None = None,
        query: str | None = None,
        visible_statuses: frozenset[TournamentStatus] | None = None,
    ) -> Select[Tournament]:
        statement = select(Tournament)

        if visible_statuses is not None:
            # Un arbitre ne voit jamais les brouillons.
            statement = statement.where(Tournament.status.in_(visible_statuses))
        if status is not None:
            statement = statement.where(Tournament.status == status)
        if city:
            statement = statement.where(func.lower(Tournament.city) == city.strip().lower())
        if upcoming is not None:
            today = date.today()
            statement = statement.where(
                Tournament.end_date >= today if upcoming else Tournament.end_date < today
            )
        if query:
            pattern = f"%{query.strip().lower()}%"
            statement = statement.where(func.lower(Tournament.title).like(pattern))
        return statement

    async def search_page(
        self, statement: Select[Tournament], *, page: int, size: int
    ) -> tuple[list[Tournament], int]:
        total = await self.count(statement)
        paged = (
            statement.order_by(Tournament.start_date.desc()).offset((page - 1) * size).limit(size)
        )
        return list((await self.session.scalars(paged)).unique()), total

    async def assignment_counts(
        self, tournament_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[int, int]]:
        """Compte, par tournoi, les désignations actives et celles confirmées.

        Une seule requête pour toute la page : évite N+1 sur la liste.
        """
        if not tournament_ids:
            return {}

        confirmed = func.sum(
            case((TournamentAssignment.status == AssignmentStatus.CONFIRMED, 1), else_=0)
        )
        statement = (
            select(
                TournamentAssignment.tournament_id,
                func.count(TournamentAssignment.id),
                confirmed,
            )
            .where(
                TournamentAssignment.tournament_id.in_(tournament_ids),
                # Les désignations annulées ne comptent pas comme un effectif.
                TournamentAssignment.status != AssignmentStatus.CANCELLED,
            )
            .group_by(TournamentAssignment.tournament_id)
        )
        rows = await self.session.execute(statement)
        return {row[0]: (int(row[1] or 0), int(row[2] or 0)) for row in rows}
