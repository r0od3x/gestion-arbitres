"""Service désignations : qui est convoqué à quel tournoi, et sa réponse."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.models.assignment import TournamentAssignment
from app.models.enums import AssignmentStatus, TournamentStatus
from app.models.referee import RefereeProfile
from app.models.tournament import Tournament
from app.models.user import User
from app.repositories.assignment import AssignmentRepository
from app.repositories.referee import RefereeRepository
from app.schemas.tournament import AssignmentsDiff
from app.services.errors import (
    InvalidStateError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.services.tournaments import TournamentService

logger = logging.getLogger(__name__)


class AssignmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.assignments = AssignmentRepository(session)
        self.referees = RefereeRepository(session)
        self.tournaments = TournamentService(session)

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------

    async def list_for_tournament(
        self, tournament_id: uuid.UUID, *, include_cancelled: bool = False
    ) -> list[TournamentAssignment]:
        await self.tournaments.get(tournament_id)
        return await self.assignments.list_for_tournament(
            tournament_id, include_cancelled=include_cancelled
        )

    async def list_for_referee(
        self, referee_id: uuid.UUID, *, upcoming: bool | None = None
    ) -> list[TournamentAssignment]:
        return await self.assignments.list_for_referee(referee_id, upcoming=upcoming)

    # ------------------------------------------------------------------
    # Mise à jour différentielle
    # ------------------------------------------------------------------

    async def replace_assignments(
        self, tournament_id: uuid.UUID, referee_ids: list[uuid.UUID], author: User
    ) -> AssignmentsDiff:
        """Aligne les désignations sur la liste fournie.

        Différentiel plutôt que remplacement : les désignations inchangées
        gardent leur identité, donc la réponse déjà donnée par un arbitre et
        l'historique de ses notifications survivent à chaque enregistrement.
        """
        tournament = await self.tournaments.get(tournament_id)
        self.tournaments.ensure_open_for_assignment(tournament)

        target = set(referee_ids)
        await self._ensure_referees_assignable(target)

        existing = await self.assignments.list_for_tournament(tournament_id, include_cancelled=True)
        by_referee = {assignment.referee_id: assignment for assignment in existing}

        added = cancelled = unchanged = 0

        for referee_id in target:
            assignment = by_referee.get(referee_id)
            if assignment is None:
                self.session.add(
                    TournamentAssignment(
                        tournament_id=tournament_id,
                        referee_id=referee_id,
                        status=AssignmentStatus.PENDING,
                        assigned_by=author.id,
                    )
                )
                added += 1
            elif assignment.status is AssignmentStatus.CANCELLED:
                # Re-convoqué après une annulation : la réponse repart à zéro.
                assignment.status = AssignmentStatus.PENDING
                assignment.responded_at = None
                assignment.assigned_by = author.id
                added += 1
            else:
                unchanged += 1

        for assignment in existing:
            if (
                assignment.referee_id not in target
                and assignment.status is not AssignmentStatus.CANCELLED
            ):
                assignment.status = AssignmentStatus.CANCELLED
                cancelled += 1

        await self.session.flush()
        logger.info(
            "Tournoi %s: %s ajout(s), %s annulation(s), %s inchangée(s)",
            tournament_id,
            added,
            cancelled,
            unchanged,
        )
        return AssignmentsDiff(added=added, cancelled=cancelled, unchanged=unchanged)

    async def _ensure_referees_assignable(self, referee_ids: set[uuid.UUID]) -> None:
        if not referee_ids:
            return

        profiles = await self.referees.get_many(sorted(referee_ids))
        found = {profile.id for profile in profiles}
        missing = referee_ids - found
        if missing:
            raise NotFoundError(
                f"{len(missing)} arbitre(s) introuvable(s) : "
                + ", ".join(str(referee_id) for referee_id in sorted(missing))
            )

        # Un compte désactivé ne doit pas recevoir de nouvelle convocation.
        inactive = [profile for profile in profiles if not profile.user.is_active]
        if inactive:
            names = ", ".join(profile.full_name for profile in inactive)
            raise ValidationError(f"Arbitre(s) désactivé(s), non convocable(s) : {names}")

    # ------------------------------------------------------------------
    # Réponse de l'arbitre
    # ------------------------------------------------------------------

    async def respond(
        self,
        assignment_id: uuid.UUID,
        referee: RefereeProfile,
        *,
        confirm: bool,
    ) -> TournamentAssignment:
        assignment = await self.assignments.get_with_relations(assignment_id)
        if assignment is None:
            raise NotFoundError("Convocation introuvable.")

        # On ne répond que pour soi.
        if assignment.referee_id != referee.id:
            raise PermissionDeniedError("Cette convocation ne vous concerne pas.")

        self._ensure_respondable(assignment, assignment.tournament)

        assignment.status = AssignmentStatus.CONFIRMED if confirm else AssignmentStatus.DECLINED
        assignment.responded_at = utcnow()
        await self.session.flush()
        return assignment

    @staticmethod
    def _ensure_respondable(assignment: TournamentAssignment, tournament: Tournament) -> None:
        if assignment.status is AssignmentStatus.CANCELLED:
            raise InvalidStateError("Cette convocation a été annulée.")
        if tournament.status is TournamentStatus.CANCELLED:
            raise InvalidStateError("Ce tournoi a été annulé.")
        if TournamentService.is_past(tournament):
            raise InvalidStateError("Ce tournoi est déjà passé.")
