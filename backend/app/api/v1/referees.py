"""Routes de gestion des arbitres. Réservées aux administrateurs.

`AdminUser` est déclaré sur le router entier : aucune route ne peut être
ajoutée ici sans contrôle de rôle.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession, require_admin
from app.core.config import settings
from app.models.enums import RefereeGrade
from app.schemas.common import Page
from app.schemas.referee import (
    RefereeAdminUpdate,
    RefereeInviteRequest,
    RefereeInviteResponse,
    RefereeRead,
)
from app.services.referees import RefereeService

router = APIRouter(
    prefix="/referees",
    tags=["referees"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=Page[RefereeRead], summary="Lister et filtrer les arbitres")
async def list_referees(
    session: DbSession,
    grade: Annotated[RefereeGrade | None, Query(description="Filtrer par grade")] = None,
    city: Annotated[str | None, Query(description="Filtrer par ville")] = None,
    active: Annotated[bool | None, Query(description="Comptes actifs ou non")] = None,
    q: Annotated[str | None, Query(description="Nom, e-mail, téléphone ou licence")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[RefereeRead]:
    profiles, total = await RefereeService(session).search(
        grade=grade, city=city, active=active, query=q, page=page, size=size
    )
    return Page[RefereeRead](
        items=[RefereeRead.from_profile(profile) for profile in profiles],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/invite",
    response_model=RefereeInviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inviter un arbitre",
)
async def invite_referee(
    payload: RefereeInviteRequest, session: DbSession
) -> RefereeInviteResponse:
    profile, invite_url = await RefereeService(session).invite(payload)
    return RefereeInviteResponse(
        referee=RefereeRead.from_profile(profile),
        invite_url=invite_url,
        invite_expires_in_hours=settings.INVITE_TOKEN_TTL_HOURS,
    )


@router.get("/{referee_id}", response_model=RefereeRead, summary="Consulter un arbitre")
async def get_referee(referee_id: uuid.UUID, session: DbSession) -> RefereeRead:
    profile = await RefereeService(session).get(referee_id)
    return RefereeRead.from_profile(profile)


@router.patch("/{referee_id}", response_model=RefereeRead, summary="Modifier un arbitre")
async def update_referee(
    referee_id: uuid.UUID, payload: RefereeAdminUpdate, session: DbSession
) -> RefereeRead:
    profile = await RefereeService(session).update_as_admin(referee_id, payload)
    return RefereeRead.from_profile(profile)


@router.post(
    "/{referee_id}/deactivate", response_model=RefereeRead, summary="Désactiver un arbitre"
)
async def deactivate_referee(referee_id: uuid.UUID, session: DbSession) -> RefereeRead:
    profile = await RefereeService(session).set_active(referee_id, active=False)
    return RefereeRead.from_profile(profile)


@router.post("/{referee_id}/activate", response_model=RefereeRead, summary="Réactiver un arbitre")
async def activate_referee(referee_id: uuid.UUID, session: DbSession) -> RefereeRead:
    profile = await RefereeService(session).set_active(referee_id, active=True)
    return RefereeRead.from_profile(profile)


@router.post(
    "/{referee_id}/invite/resend",
    response_model=RefereeInviteResponse,
    summary="Régénérer le lien d'invitation",
)
async def resend_invite(referee_id: uuid.UUID, session: DbSession) -> RefereeInviteResponse:
    service = RefereeService(session)
    invite_url = await service.resend_invite(referee_id)
    profile = await service.get(referee_id)
    return RefereeInviteResponse(
        referee=RefereeRead.from_profile(profile),
        invite_url=invite_url,
        invite_expires_in_hours=settings.INVITE_TOKEN_TTL_HOURS,
    )
