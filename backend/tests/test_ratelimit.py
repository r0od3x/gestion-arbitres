"""Limitation de débit sur la connexion."""

import pytest
from httpx import AsyncClient

from app.core.ratelimit import RateLimitError, SlidingWindowLimiter, login_limiter
from app.models import User


def test_la_fenetre_glissante_bloque_au_dela_du_quota() -> None:
    limiter = SlidingWindowLimiter(max_calls=3, window_seconds=60)

    for _ in range(3):
        limiter.check("1.2.3.4")

    with pytest.raises(RateLimitError):
        limiter.check("1.2.3.4")

    # Les clés sont indépendantes.
    limiter.check("5.6.7.8")


def test_reset_libere_la_cle() -> None:
    limiter = SlidingWindowLimiter(max_calls=1, window_seconds=60)
    limiter.check("ip")
    with pytest.raises(RateLimitError):
        limiter.check("ip")

    limiter.reset("ip")
    limiter.check("ip")


async def test_trop_de_tentatives_de_connexion_renvoie_429(
    client: AsyncClient, admin: User
) -> None:
    payload = {"email": admin.email, "password": "mauvais-mot-de-passe"}

    for _ in range(login_limiter.max_calls):
        assert (await client.post("/auth/login", json=payload)).status_code == 401

    response = await client.post("/auth/login", json=payload)
    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
