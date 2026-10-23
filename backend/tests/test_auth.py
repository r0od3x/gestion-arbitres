"""Connexion, rafraîchissement, invitation, et refus d'accès."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, decode_token
from app.models import User, UserRole
from app.services.auth import AuthService
from tests.conftest import ADMIN_PASSWORD, REFEREE_PASSWORD, auth_header, login


async def test_login_reussi_retourne_un_jeton_et_pose_le_cookie(
    client: AsyncClient, admin: User
) -> None:
    response = await client.post(
        "/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_TTL_MINUTES * 60

    payload = decode_token(body["access_token"], "access")
    assert payload["sub"] == str(admin.id)
    assert payload["role"] == UserRole.ADMIN.value

    cookie = response.cookies.get(settings.REFRESH_COOKIE_NAME)
    assert cookie, "le cookie de rafraîchissement doit être posé"
    assert "httponly" in response.headers["set-cookie"].lower()


async def test_login_insensible_a_la_casse_de_l_email(client: AsyncClient, admin: User) -> None:
    response = await client.post(
        "/auth/login", json={"email": admin.email.upper(), "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200


async def test_login_mauvais_mot_de_passe_refuse(client: AsyncClient, admin: User) -> None:
    response = await client.post(
        "/auth/login", json={"email": admin.email, "password": "mauvais-mot-de-passe"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


async def test_login_email_inconnu_donne_le_meme_message(client: AsyncClient) -> None:
    """Pas de fuite d'information : inconnu et mauvais mot de passe sont indistinguables."""
    response = await client.post(
        "/auth/login", json={"email": "inconnu@test.ma", "password": "peu-importe"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou mot de passe incorrect."


async def test_login_compte_desactive_refuse(
    client: AsyncClient, session: AsyncSession, admin: User
) -> None:
    admin.is_active = False
    session.add(admin)
    await session.commit()

    response = await client.post(
        "/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 401
    assert "désactivé" in response.json()["detail"]


async def test_refresh_renouvelle_le_jeton(client: AsyncClient, admin: User) -> None:
    await login(client, admin.email, ADMIN_PASSWORD)  # pose le cookie sur le client

    response = await client.post("/auth/refresh")
    assert response.status_code == 200
    assert decode_token(response.json()["access_token"], "access")["sub"] == str(admin.id)


async def test_refresh_sans_cookie_refuse(client: AsyncClient) -> None:
    response = await client.post("/auth/refresh")
    assert response.status_code == 401


async def test_refresh_rejette_un_jeton_d_acces(client: AsyncClient, admin: User) -> None:
    """Un jeton d'accès ne doit pas pouvoir servir de jeton de rafraîchissement."""
    access_token = create_access_token(admin.id, admin.role.value)
    client.cookies.set(settings.REFRESH_COOKIE_NAME, access_token)

    response = await client.post("/auth/refresh")
    assert response.status_code == 401


async def test_logout_efface_le_cookie(client: AsyncClient, admin: User) -> None:
    await login(client, admin.email, ADMIN_PASSWORD)

    response = await client.post("/auth/logout")
    assert response.status_code == 200
    assert not response.cookies.get(settings.REFRESH_COOKIE_NAME)


async def test_me_retourne_le_profil_arbitre(client: AsyncClient, referee: User) -> None:
    token = await login(client, referee.email, REFEREE_PASSWORD)

    response = await client.get("/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == referee.email
    assert body["role"] == UserRole.REFEREE.value
    assert body["referee_profile"]["first_name"] == "Youssef"
    # Le champ réservé aux admins n'est pas exposé.
    assert "notes_admin" not in body["referee_profile"]


async def test_me_sans_jeton_refuse(client: AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_me_avec_jeton_invalide_refuse(client: AsyncClient) -> None:
    response = await client.get("/auth/me", headers=auth_header("pas-un-jeton"))
    assert response.status_code == 401


async def test_accept_invite_definit_le_mot_de_passe(
    client: AsyncClient, session: AsyncSession
) -> None:
    invite = User(email="nouveau@test.ma", password_hash=None, role=UserRole.REFEREE)
    session.add(invite)
    await session.commit()

    token = AuthService(session).create_invite_token(invite)
    response = await client.post(
        "/auth/accept-invite", json={"token": token, "password": "NouveauPass!2026"}
    )
    assert response.status_code == 200

    # Le compte est désormais utilisable.
    login_response = await client.post(
        "/auth/login", json={"email": invite.email, "password": "NouveauPass!2026"}
    )
    assert login_response.status_code == 200


async def test_accept_invite_deux_fois_refuse(client: AsyncClient, session: AsyncSession) -> None:
    invite = User(email="double@test.ma", password_hash=None, role=UserRole.REFEREE)
    session.add(invite)
    await session.commit()
    token = AuthService(session).create_invite_token(invite)

    first = await client.post(
        "/auth/accept-invite", json={"token": token, "password": "PremierPass!2026"}
    )
    assert first.status_code == 200

    second = await client.post(
        "/auth/accept-invite", json={"token": token, "password": "SecondPass!2026"}
    )
    assert second.status_code == 409


async def test_accept_invite_mot_de_passe_trop_court_refuse(
    client: AsyncClient, session: AsyncSession
) -> None:
    invite = User(email="court@test.ma", password_hash=None, role=UserRole.REFEREE)
    session.add(invite)
    await session.commit()
    token = AuthService(session).create_invite_token(invite)

    response = await client.post("/auth/accept-invite", json={"token": token, "password": "court"})
    assert response.status_code == 422


async def test_utilisateur_sans_mot_de_passe_ne_peut_pas_se_connecter(
    client: AsyncClient, session: AsyncSession
) -> None:
    """Invitation non acceptée = pas de connexion possible."""
    invite = User(email="attente@test.ma", password_hash=None, role=UserRole.REFEREE)
    session.add(invite)
    await session.commit()

    response = await client.post(
        "/auth/login", json={"email": invite.email, "password": "nimporte-quoi"}
    )
    assert response.status_code == 401
