"""Routes de l'arbitre connecté.

`RefereeUser` résout le profil de l'appelant : aucune de ces routes ne prend
d'identifiant d'arbitre, donc aucune ne peut servir à lire ou modifier le
profil de quelqu'un d'autre.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, RefereeUser
from app.schemas.tournament import AssignmentWithTournament
from app.schemas.user import MeRead, RefereeProfileRead, RefereeProfileUpdate
from app.services.assignments import AssignmentService
from app.services.referees import RefereeService

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeRead, summary="Mon compte")
async def read_me(user: CurrentUser) -> MeRead:
    return MeRead.model_validate(user)


@router.get("/profile", response_model=RefereeProfileRead, summary="Mon profil arbitre")
async def read_my_profile(profile: RefereeUser) -> RefereeProfileRead:
    return RefereeProfileRead.model_validate(profile)


@router.patch("/profile", response_model=RefereeProfileRead, summary="Modifier mon profil")
async def update_my_profile(
    payload: RefereeProfileUpdate, profile: RefereeUser, session: DbSession
) -> RefereeProfileRead:
    updated = await RefereeService(session).update_own_profile(profile, payload)
    return RefereeProfileRead.model_validate(updated)


# ----------------------------------------------------------------------
# Convocations de l'arbitre connecté
# ----------------------------------------------------------------------


@router.get(
    "/assignments",
    response_model=list[AssignmentWithTournament],
    summary="Mes convocations",
)
async def list_my_assignments(
    profile: RefereeUser,
    session: DbSession,
    upcoming: Annotated[bool | None, Query(description="À venir (true) ou passées (false)")] = None,
) -> list[AssignmentWithTournament]:
    assignments = await AssignmentService(session).list_for_referee(profile.id, upcoming=upcoming)
    return [AssignmentWithTournament.from_assignment(a) for a in assignments]


@router.post(
    "/assignments/{assignment_id}/confirm",
    response_model=AssignmentWithTournament,
    summary="Confirmer ma présence",
)
async def confirm_assignment(
    assignment_id: uuid.UUID, profile: RefereeUser, session: DbSession
) -> AssignmentWithTournament:
    assignment = await AssignmentService(session).respond(assignment_id, profile, confirm=True)
    return AssignmentWithTournament.from_assignment(assignment)


@router.post(
    "/assignments/{assignment_id}/decline",
    response_model=AssignmentWithTournament,
    summary="Décliner la convocation",
)
async def decline_assignment(
    assignment_id: uuid.UUID, profile: RefereeUser, session: DbSession
) -> AssignmentWithTournament:
    assignment = await AssignmentService(session).respond(assignment_id, profile, confirm=False)
    return AssignmentWithTournament.from_assignment(assignment)
