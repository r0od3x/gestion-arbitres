"""Routes de l'arbitre connecté : profil et consentement WhatsApp."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import RefereeGrade, RefereeProfile, User, UserRole
from tests.conftest import ADMIN_PASSWORD, REFEREE_PASSWORD, auth_header, login


async def referee_token(client: AsyncClient, referee: User) -> str:
    return await login(client, referee.email, REFEREE_PASSWORD)


async def test_lecture_de_mon_compte(client: AsyncClient, referee: User) -> None:
    token = await referee_token(client, referee)

    response = await client.get("/me", headers=auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == referee.email
    assert body["referee_profile"]["first_name"] == "Youssef"


async def test_lecture_de_mon_profil(client: AsyncClient, referee: User) -> None:
    token = await referee_token(client, referee)

    response = await client.get("/me/profile", headers=auth_header(token))

    assert response.status_code == 200
    # Les notes administrateur ne sont jamais exposées à l'arbitre.
    assert "notes_admin" not in response.json()


async def test_modification_de_mon_profil(client: AsyncClient, referee: User) -> None:
    token = await referee_token(client, referee)

    response = await client.patch(
        "/me/profile",
        json={"city": "Tanger", "club": "Ittihad Tanger"},
        headers=auth_header(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["city"] == "Tanger"
    assert body["club"] == "Ittihad Tanger"
    assert body["first_name"] == "Youssef"  # inchangé


async def test_le_telephone_est_normalise_en_e164(client: AsyncClient, referee: User) -> None:
    token = await referee_token(client, referee)

    response = await client.patch(
        "/me/profile", json={"phone": "06 12 34 56 80"}, headers=auth_header(token)
    )

    assert response.status_code == 200
    assert response.json()["phone_e164"] == "+212612345680"


async def test_telephone_invalide_refuse(client: AsyncClient, referee: User) -> None:
    token = await referee_token(client, referee)

    response = await client.patch("/me/profile", json={"phone": "abc"}, headers=auth_header(token))

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_telephone_deja_pris_par_un_autre_arbitre(
    client: AsyncClient, referee: User, session: AsyncSession
) -> None:
    autre = User(
        email="autre@test.ma",
        password_hash=hash_password(REFEREE_PASSWORD),
        role=UserRole.REFEREE,
    )
    autre.referee_profile = RefereeProfile(
        first_name="Autre",
        last_name="Arbitre",
        phone_e164="+212612345690",
        grade=RefereeGrade.REGIONAL,
    )
    session.add(autre)
    await session.commit()

    token = await referee_token(client, referee)
    response = await client.patch(
        "/me/profile", json={"phone": "+212612345690"}, headers=auth_header(token)
    )

    assert response.status_code == 409


async def test_garder_son_propre_numero_est_accepte(client: AsyncClient, referee: User) -> None:
    """Renvoyer le même numéro ne doit pas déclencher un conflit avec soi-même."""
    token = await referee_token(client, referee)

    response = await client.patch(
        "/me/profile", json={"phone": "+212612345671"}, headers=auth_header(token)
    )

    assert response.status_code == 200
    assert response.json()["phone_e164"] == "+212612345671"


# ----------------------------------------------------------------------
# Consentement WhatsApp
# ----------------------------------------------------------------------


async def test_le_consentement_est_horodate(client: AsyncClient, session: AsyncSession) -> None:
    sans_consentement = User(
        email="sans.consentement@test.ma",
        password_hash=hash_password(REFEREE_PASSWORD),
        role=UserRole.REFEREE,
    )
    sans_consentement.referee_profile = RefereeProfile(
        first_name="Nadia",
        last_name="Tazi",
        phone_e164="+212612345691",
        grade=RefereeGrade.REGIONAL,
        whatsapp_opt_in=False,
    )
    session.add(sans_consentement)
    await session.commit()

    token = await login(client, sans_consentement.email, REFEREE_PASSWORD)
    response = await client.patch(
        "/me/profile", json={"whatsapp_opt_in": True}, headers=auth_header(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["whatsapp_opt_in"] is True
    assert body["whatsapp_opt_in_at"] is not None


async def test_le_retrait_du_consentement_efface_l_horodatage(
    client: AsyncClient, referee: User
) -> None:
    token = await referee_token(client, referee)

    response = await client.patch(
        "/me/profile", json={"whatsapp_opt_in": False}, headers=auth_header(token)
    )

    assert response.status_code == 200
    assert response.json()["whatsapp_opt_in"] is False
    assert response.json()["whatsapp_opt_in_at"] is None


async def test_consentement_sans_numero_refuse(client: AsyncClient, session: AsyncSession) -> None:
    """On ne peut pas consentir à WhatsApp sans numéro joignable."""
    sans_numero = User(
        email="sans.numero@test.ma",
        password_hash=hash_password(REFEREE_PASSWORD),
        role=UserRole.REFEREE,
    )
    sans_numero.referee_profile = RefereeProfile(
        first_name="Karim",
        last_name="Ouazzani",
        phone_e164=None,
        grade=RefereeGrade.REGIONAL,
    )
    session.add(sans_numero)
    await session.commit()

    token = await login(client, sans_numero.email, REFEREE_PASSWORD)
    response = await client.patch(
        "/me/profile", json={"whatsapp_opt_in": True}, headers=auth_header(token)
    )

    assert response.status_code == 422
    assert "téléphone" in response.json()["detail"]


# ----------------------------------------------------------------------
# Autorisation : un arbitre ne peut ni s'élever, ni toucher à autrui
# ----------------------------------------------------------------------


async def test_un_arbitre_ne_peut_pas_changer_son_grade(client: AsyncClient, referee: User) -> None:
    token = await referee_token(client, referee)

    response = await client.patch(
        "/me/profile", json={"grade": "international"}, headers=auth_header(token)
    )

    # Le champ n'existe pas dans le schéma : la requête est rejetée, pas ignorée.
    assert response.status_code == 422


async def test_un_arbitre_ne_peut_pas_ecrire_les_notes_admin(
    client: AsyncClient, referee: User
) -> None:
    token = await referee_token(client, referee)

    response = await client.patch(
        "/me/profile", json={"notes_admin": "je suis formidable"}, headers=auth_header(token)
    )
    assert response.status_code == 422


async def test_un_arbitre_ne_peut_pas_changer_son_numero_de_licence(
    client: AsyncClient, referee: User
) -> None:
    token = await referee_token(client, referee)

    response = await client.patch(
        "/me/profile", json={"license_number": "ARB-999"}, headers=auth_header(token)
    )
    assert response.status_code == 422


async def test_me_refuse_a_un_anonyme(client: AsyncClient) -> None:
    for method, path in [("get", "/me"), ("get", "/me/profile")]:
        response = await getattr(client, method)(path)
        assert response.status_code == 401, path


async def test_profil_refuse_a_un_admin(client: AsyncClient, admin: User) -> None:
    """Un administrateur n'a pas de profil arbitre : ces routes ne le concernent pas."""
    token = await login(client, admin.email, ADMIN_PASSWORD)

    response = await client.get("/me/profile", headers=auth_header(token))

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


async def test_un_arbitre_desactive_perd_l_acces(
    client: AsyncClient, referee: User, session: AsyncSession
) -> None:
    token = await referee_token(client, referee)

    referee.is_active = False
    session.add(referee)
    await session.commit()

    response = await client.get("/me", headers=auth_header(token))
    assert response.status_code == 401
