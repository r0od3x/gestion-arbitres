"""Routes de l'arbitre connecté.

`RefereeUser` résout le profil de l'appelant : aucune de ces routes ne prend
d'identifiant d'arbitre, donc aucune ne peut servir à lire ou modifier le
profil de quelqu'un d'autre.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, RefereeUser
from app.schemas.user import MeRead, RefereeProfileRead, RefereeProfileUpdate
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
