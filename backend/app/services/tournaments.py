"""Service tournois : création, modification, transitions de statut.

La machine à états vit dans `models/enums.py` (`TOURNAMENT_TRANSITIONS`).
Ce service l'applique, il ne la réécrit pas.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TOURNAMENT_TRANSITIONS, TournamentStatus
from app.models.tournament import Tournament
from app.models.user import User
from app.repositories.tournament import TournamentRepository
from app.schemas.tournament import TournamentCreate, TournamentUpdate
from app.services.errors import InvalidStateError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

#: Statuts qu'un arbitre peut voir. Les brouillons ne sortent jamais de l'admin.
REFEREE_VISIBLE_STATUSES = frozenset(
    {TournamentStatus.PUBLISHED, TournamentStatus.CANCELLED, TournamentStatus.COMPLETED}
)

#: Un tournoi figé n'accepte plus ni modification ni désignation.
FROZEN_STATUSES = frozenset({TournamentStatus.CANCELLED, TournamentStatus.COMPLETED})


class TournamentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tournaments = TournamentRepository(session)

    async def get(self, tournament_id: uuid.UUID) -> Tournament:
        tournament = await self.tournaments.get(tournament_id)
        if tournament is None:
            raise NotFoundError("Tournoi introuvable.")
        return tournament

    async def get_visible_for_referee(self, tournament_id: uuid.UUID) -> Tournament:
        tournament = await self.get(tournament_id)
        if tournament.status not in REFEREE_VISIBLE_STATUSES:
            # Un brouillon n'existe pas du point de vue d'un arbitre.
            raise NotFoundError("Tournoi introuvable.")
        return tournament

    async def search(
        self,
        *,
        status: TournamentStatus | None = None,
        city: str | None = None,
        upcoming: bool | None = None,
        query: str | None = None,
        for_referee: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Tournament], int, dict[uuid.UUID, tuple[int, int]]]:
        statement = self.tournaments.search_statement(
            status=status,
            city=city,
            upcoming=upcoming,
            query=query,
            visible_statuses=REFEREE_VISIBLE_STATUSES if for_referee else None,
        )
        rows, total = await self.tournaments.search_page(statement, page=page, size=size)
        counts = await self.tournaments.assignment_counts([row.id for row in rows])
        return rows, total, counts

    async def create(self, payload: TournamentCreate, author: User) -> Tournament:
        tournament = Tournament(
            **payload.model_dump(),
            status=TournamentStatus.DRAFT,
            created_by=author.id,
        )
        self.session.add(tournament)
        await self.session.flush()
        logger.info("Tournoi créé: %s (%s)", tournament.title, tournament.id)
        return tournament

    async def update(self, tournament_id: uuid.UUID, payload: TournamentUpdate) -> Tournament:
        tournament = await self.get(tournament_id)
        if tournament.status in FROZEN_STATUSES:
            raise InvalidStateError(
                f"Un tournoi {_label(tournament.status)} ne peut plus être modifié."
            )

        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(tournament, field, value)

        # Les deux dates peuvent changer séparément : revalider le couple final.
        if tournament.end_date < tournament.start_date:
            raise ValidationError("La date de fin ne peut pas précéder la date de début.")

        await self.session.flush()
        return tournament

    async def change_status(self, tournament_id: uuid.UUID, target: TournamentStatus) -> Tournament:
        """Applique une transition si elle est autorisée."""
        tournament = await self.get(tournament_id)
        current = tournament.status

        if target == current:
            raise InvalidStateError(f"Ce tournoi est déjà {_label(target)}.")
        if target not in TOURNAMENT_TRANSITIONS[current]:
            raise InvalidStateError(
                f"Transition interdite : un tournoi {_label(current)} "
                f"ne peut pas passer à {_label(target)}."
            )

        tournament.status = target
        await self.session.flush()
        logger.info("Tournoi %s: %s → %s", tournament_id, current, target)
        return tournament

    @staticmethod
    def ensure_open_for_assignment(tournament: Tournament) -> None:
        """Vérifie qu'on peut encore désigner des arbitres sur ce tournoi."""
        if tournament.status in FROZEN_STATUSES:
            raise InvalidStateError(
                f"Un tournoi {_label(tournament.status)} n'accepte plus de convocation."
            )

    @staticmethod
    def is_past(tournament: Tournament) -> bool:
        return tournament.end_date < date.today()


_LABELS: dict[TournamentStatus, str] = {
    TournamentStatus.DRAFT: "en brouillon",
    TournamentStatus.PUBLISHED: "publié",
    TournamentStatus.CANCELLED: "annulé",
    TournamentStatus.COMPLETED: "terminé",
}


def _label(status: TournamentStatus) -> str:
    return _LABELS[status]
