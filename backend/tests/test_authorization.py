"""Contrôle des rôles : les dépendances sont le seul point d'autorisation."""

import pytest

from app.api.deps import require_admin, require_referee_profile
from app.models import User
from app.services.errors import PermissionDeniedError


async def test_require_admin_accepte_un_admin(admin: User) -> None:
    assert await require_admin(admin) is admin


async def test_require_admin_refuse_un_arbitre(referee: User) -> None:
    with pytest.raises(PermissionDeniedError):
        await require_admin(referee)


async def test_require_referee_accepte_un_arbitre(referee: User) -> None:
    profile = await require_referee_profile(referee)
    assert profile.first_name == "Youssef"


async def test_require_referee_refuse_un_admin(admin: User) -> None:
    """Un admin n'a pas de profil arbitre : il ne passe pas par les routes /me."""
    with pytest.raises(PermissionDeniedError):
        await require_referee_profile(admin)
