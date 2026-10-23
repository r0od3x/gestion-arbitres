"""Routes tournois et désignations.

Lecture ouverte aux deux rôles (un arbitre ne voit jamais les brouillons) ;
écriture réservée aux administrateurs, route par route.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AdminUser, CurrentUser, DbSession, require_admin
from app.models.enums import TournamentStatus
from app.schemas.common import Page
from app.schemas.tournament import (
    AssignmentsDiff,
    AssignmentsReplace,
    AssignmentWithReferee,
    TournamentCreate,
    TournamentRead,
    TournamentUpdate,
    TournamentWithCounts,
)
from app.services.assignments import AssignmentService
from app.services.tournaments import TournamentService

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.get("", response_model=Page[TournamentWithCounts], summary="Lister les tournois")
async def list_tournaments(
    user: CurrentUser,
    session: DbSession,
    status_filter: Annotated[
        TournamentStatus | None, Query(alias="status", description="Filtrer par statut")
    ] = None,
    city: Annotated[str | None, Query(description="Filtrer par ville")] = None,
    upcoming: Annotated[bool | None, Query(description="À venir ou passés")] = None,
    q: Annotated[str | None, Query(description="Recherche sur le titre")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[TournamentWithCounts]:
    rows, total, counts = await TournamentService(session).search(
        status=status_filter,
        city=city,
        upcoming=upcoming,
        query=q,
        for_referee=not user.is_admin,
        page=page,
        size=size,
    )
    return Page[TournamentWithCounts](
        items=[
            TournamentWithCounts.from_row(tournament, *counts.get(tournament.id, (0, 0)))
            for tournament in rows
        ],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "",
    response_model=TournamentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un tournoi (brouillon)",
)
async def create_tournament(
    payload: TournamentCreate, admin: AdminUser, session: DbSession
) -> TournamentRead:
    tournament = await TournamentService(session).create(payload, admin)
    return TournamentRead.model_validate(tournament)


@router.get("/{tournament_id}", response_model=TournamentRead, summary="Consulter un tournoi")
async def get_tournament(
    tournament_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> TournamentRead:
    service = TournamentService(session)
    tournament = (
        await service.get(tournament_id)
        if user.is_admin
        else await service.get_visible_for_referee(tournament_id)
    )
    return TournamentRead.model_validate(tournament)


@router.patch(
    "/{tournament_id}",
    response_model=TournamentRead,
    dependencies=[Depends(require_admin)],
    summary="Modifier un tournoi",
)
async def update_tournament(
    tournament_id: uuid.UUID, payload: TournamentUpdate, session: DbSession
) -> TournamentRead:
    tournament = await TournamentService(session).update(tournament_id, payload)
    return TournamentRead.model_validate(tournament)


@router.post(
    "/{tournament_id}/publish",
    response_model=TournamentRead,
    dependencies=[Depends(require_admin)],
    summary="Publier un tournoi",
)
async def publish_tournament(tournament_id: uuid.UUID, session: DbSession) -> TournamentRead:
    tournament = await TournamentService(session).change_status(
        tournament_id, TournamentStatus.PUBLISHED
    )
    return TournamentRead.model_validate(tournament)


@router.post(
    "/{tournament_id}/cancel",
    response_model=TournamentRead,
    dependencies=[Depends(require_admin)],
    summary="Annuler un tournoi",
)
async def cancel_tournament(tournament_id: uuid.UUID, session: DbSession) -> TournamentRead:
    tournament = await TournamentService(session).change_status(
        tournament_id, TournamentStatus.CANCELLED
    )
    return TournamentRead.model_validate(tournament)


@router.post(
    "/{tournament_id}/complete",
    response_model=TournamentRead,
    dependencies=[Depends(require_admin)],
    summary="Clôturer un tournoi",
)
async def complete_tournament(tournament_id: uuid.UUID, session: DbSession) -> TournamentRead:
    tournament = await TournamentService(session).change_status(
        tournament_id, TournamentStatus.COMPLETED
    )
    return TournamentRead.model_validate(tournament)


# ----------------------------------------------------------------------
# Désignations
# ----------------------------------------------------------------------


@router.get(
    "/{tournament_id}/assignments",
    response_model=list[AssignmentWithReferee],
    dependencies=[Depends(require_admin)],
    summary="Arbitres convoqués",
)
async def list_assignments(
    tournament_id: uuid.UUID,
    session: DbSession,
    include_cancelled: Annotated[bool, Query(description="Inclure les annulées")] = False,
) -> list[AssignmentWithReferee]:
    assignments = await AssignmentService(session).list_for_tournament(
        tournament_id, include_cancelled=include_cancelled
    )
    return [AssignmentWithReferee.from_assignment(a) for a in assignments]


@router.put(
    "/{tournament_id}/assignments",
    response_model=AssignmentsDiff,
    dependencies=[Depends(require_admin)],
    summary="Définir la liste des arbitres convoqués",
)
async def replace_assignments(
    tournament_id: uuid.UUID,
    payload: AssignmentsReplace,
    admin: AdminUser,
    session: DbSession,
) -> AssignmentsDiff:
    """Mise à jour différentielle : ajoute les nouveaux, annule les retirés,
    laisse les autres intacts avec leur réponse déjà donnée."""
    return await AssignmentService(session).replace_assignments(
        tournament_id, payload.referee_ids, admin
    )
