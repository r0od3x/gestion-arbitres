"""Routes arbitres (espace administrateur) : invitation, recherche, édition, désactivation."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import RefereeGrade, RefereeProfile, User, UserRole
from tests.conftest import ADMIN_PASSWORD, REFEREE_PASSWORD, auth_header, login

INVITE = {
    "email": "nouvel.arbitre@test.ma",
    "first_name": "Imane",
    "last_name": "Cherkaoui",
    "phone": "0612345699",
    "grade": "national",
    "city": "Rabat",
}


async def admin_token(client: AsyncClient, admin: User) -> str:
    return await login(client, admin.email, ADMIN_PASSWORD)


# ----------------------------------------------------------------------
# Invitation
# ----------------------------------------------------------------------


async def test_invitation_cree_un_compte_sans_mot_de_passe(
    client: AsyncClient, admin: User
) -> None:
    token = await admin_token(client, admin)

    response = await client.post("/referees/invite", json=INVITE, headers=auth_header(token))

    assert response.status_code == 201, response.text
    body = response.json()
    referee = body["referee"]
    assert referee["email"] == INVITE["email"]
    assert referee["first_name"] == "Imane"
    assert referee["grade"] == "national"
    # Le compte existe mais n'est pas encore activé.
    assert referee["has_accepted_invite"] is False
    assert referee["is_active"] is True
    # Le consentement WhatsApp ne peut pas être donné par l'administrateur.
    assert referee["whatsapp_opt_in"] is False
    assert referee["whatsapp_opt_in_at"] is None

    assert body["invite_url"].startswith("http")
    assert "token=" in body["invite_url"]
    assert body["invite_expires_in_hours"] == 72


async def test_invitation_normalise_le_telephone_en_e164(client: AsyncClient, admin: User) -> None:
    token = await admin_token(client, admin)

    response = await client.post("/referees/invite", json=INVITE, headers=auth_header(token))

    assert response.json()["referee"]["phone_e164"] == "+212612345699"


async def test_invitation_refuse_un_telephone_invalide(client: AsyncClient, admin: User) -> None:
    token = await admin_token(client, admin)

    response = await client.post(
        "/referees/invite",
        json={**INVITE, "phone": "123"},
        headers=auth_header(token),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_invitation_refuse_un_email_deja_utilise(
    client: AsyncClient, admin: User, referee: User
) -> None:
    token = await admin_token(client, admin)

    response = await client.post(
        "/referees/invite",
        json={**INVITE, "email": referee.email},
        headers=auth_header(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "conflict"


async def test_invitation_refuse_un_telephone_deja_utilise(
    client: AsyncClient, admin: User, referee: User
) -> None:
    token = await admin_token(client, admin)

    response = await client.post(
        "/referees/invite",
        json={**INVITE, "phone": "+212612345671"},  # celui de la fixture
        headers=auth_header(token),
    )
    assert response.status_code == 409


async def test_le_lien_d_invitation_permet_de_definir_son_mot_de_passe(
    client: AsyncClient, admin: User
) -> None:
    """Parcours complet : l'admin invite, l'arbitre active son compte et se connecte."""
    token = await admin_token(client, admin)
    invite = await client.post("/referees/invite", json=INVITE, headers=auth_header(token))
    invite_token = invite.json()["invite_url"].split("token=")[1]

    accepted = await client.post(
        "/auth/accept-invite", json={"token": invite_token, "password": "ArbitrePass!2026"}
    )
    assert accepted.status_code == 200

    logged_in = await client.post(
        "/auth/login", json={"email": INVITE["email"], "password": "ArbitrePass!2026"}
    )
    assert logged_in.status_code == 200


async def test_renvoi_d_invitation_refuse_si_compte_deja_actif(
    client: AsyncClient, admin: User, referee: User
) -> None:
    token = await admin_token(client, admin)
    assert referee.referee_profile is not None

    response = await client.post(
        f"/referees/{referee.referee_profile.id}/invite/resend", headers=auth_header(token)
    )
    assert response.status_code == 409


# ----------------------------------------------------------------------
# Recherche et filtres
# ----------------------------------------------------------------------


async def _add_referee(
    session: AsyncSession,
    *,
    email: str,
    first: str,
    last: str,
    city: str,
    grade: RefereeGrade,
    phone: str,
    active: bool = True,
) -> None:
    user = User(
        email=email,
        password_hash=hash_password(REFEREE_PASSWORD),
        role=UserRole.REFEREE,
        is_active=active,
    )
    user.referee_profile = RefereeProfile(
        first_name=first, last_name=last, city=city, grade=grade, phone_e164=phone
    )
    session.add(user)
    await session.commit()


async def test_liste_paginee_et_triee(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    await _add_referee(
        session,
        email="a@test.ma",
        first="Amine",
        last="Alaoui",
        city="Fès",
        grade=RefereeGrade.REGIONAL,
        phone="+212612345601",
    )
    await _add_referee(
        session,
        email="b@test.ma",
        first="Btissam",
        last="Zouhair",
        city="Fès",
        grade=RefereeGrade.NATIONAL,
        phone="+212612345602",
    )
    token = await admin_token(client, admin)

    response = await client.get("/referees?size=1", headers=auth_header(token))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["size"] == 1
    assert len(body["items"]) == 1
    # Tri par nom de famille : Alaoui avant Zouhair.
    assert body["items"][0]["last_name"] == "Alaoui"


async def test_filtre_par_grade(client: AsyncClient, admin: User, session: AsyncSession) -> None:
    await _add_referee(
        session,
        email="a@test.ma",
        first="Amine",
        last="Alaoui",
        city="Fès",
        grade=RefereeGrade.REGIONAL,
        phone="+212612345601",
    )
    await _add_referee(
        session,
        email="b@test.ma",
        first="Btissam",
        last="Zouhair",
        city="Fès",
        grade=RefereeGrade.NATIONAL,
        phone="+212612345602",
    )
    token = await admin_token(client, admin)

    response = await client.get("/referees?grade=national", headers=auth_header(token))

    assert response.json()["total"] == 1
    assert response.json()["items"][0]["grade"] == "national"


async def test_filtre_par_ville_insensible_a_la_casse(
    client: AsyncClient, admin: User, referee: User
) -> None:
    token = await admin_token(client, admin)

    response = await client.get("/referees?city=casablanca", headers=auth_header(token))

    assert response.json()["total"] == 1


async def test_filtre_par_compte_actif(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    await _add_referee(
        session,
        email="inactif@test.ma",
        first="Omar",
        last="Bennis",
        city="Agadir",
        grade=RefereeGrade.REGIONAL,
        phone="+212612345603",
        active=False,
    )
    token = await admin_token(client, admin)

    actifs = await client.get("/referees?active=true", headers=auth_header(token))
    inactifs = await client.get("/referees?active=false", headers=auth_header(token))

    assert actifs.json()["total"] == 0
    assert inactifs.json()["total"] == 1


async def test_recherche_texte_sur_nom_email_et_telephone(
    client: AsyncClient, admin: User, referee: User
) -> None:
    token = await admin_token(client, admin)

    for query in ("amrani", "ARBITRE@test.ma", "212612345671"):
        response = await client.get(f"/referees?q={query}", headers=auth_header(token))
        assert response.json()["total"] == 1, f"recherche {query!r}"

    vide = await client.get("/referees?q=introuvable", headers=auth_header(token))
    assert vide.json()["total"] == 0


# ----------------------------------------------------------------------
# Consultation et modification
# ----------------------------------------------------------------------


async def test_consultation_expose_les_champs_admin(
    client: AsyncClient, admin: User, referee: User
) -> None:
    token = await admin_token(client, admin)
    assert referee.referee_profile is not None

    response = await client.get(
        f"/referees/{referee.referee_profile.id}", headers=auth_header(token)
    )

    assert response.status_code == 200
    assert "notes_admin" in response.json()


async def test_arbitre_introuvable(client: AsyncClient, admin: User) -> None:
    token = await admin_token(client, admin)

    response = await client.get(
        "/referees/00000000-0000-0000-0000-000000000000", headers=auth_header(token)
    )
    assert response.status_code == 404


async def test_modification_par_admin(client: AsyncClient, admin: User, referee: User) -> None:
    token = await admin_token(client, admin)
    assert referee.referee_profile is not None

    response = await client.patch(
        f"/referees/{referee.referee_profile.id}",
        json={"grade": "international", "notes_admin": "Disponible le week-end"},
        headers=auth_header(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["grade"] == "international"
    assert body["notes_admin"] == "Disponible le week-end"
    # Les champs non transmis ne bougent pas.
    assert body["first_name"] == "Youssef"


async def test_modification_refuse_un_champ_inconnu(
    client: AsyncClient, admin: User, referee: User
) -> None:
    token = await admin_token(client, admin)
    assert referee.referee_profile is not None

    response = await client.patch(
        f"/referees/{referee.referee_profile.id}",
        json={"role": "admin"},
        headers=auth_header(token),
    )
    assert response.status_code == 422


async def test_desactivation_puis_reactivation(
    client: AsyncClient, admin: User, referee: User
) -> None:
    token = await admin_token(client, admin)
    assert referee.referee_profile is not None
    referee_id = referee.referee_profile.id

    deactivated = await client.post(
        f"/referees/{referee_id}/deactivate", headers=auth_header(token)
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    # Un compte désactivé ne peut plus se connecter.
    refused = await client.post(
        "/auth/login", json={"email": referee.email, "password": REFEREE_PASSWORD}
    )
    assert refused.status_code == 401

    reactivated = await client.post(f"/referees/{referee_id}/activate", headers=auth_header(token))
    assert reactivated.json()["is_active"] is True


# ----------------------------------------------------------------------
# Autorisation
# ----------------------------------------------------------------------


async def test_routes_admin_refusees_a_un_anonyme(client: AsyncClient) -> None:
    for method, path in [
        ("get", "/referees"),
        ("post", "/referees/invite"),
        ("get", "/referees/00000000-0000-0000-0000-000000000000"),
    ]:
        response = await getattr(client, method)(path)
        assert response.status_code == 401, f"{method.upper()} {path}"


async def test_routes_admin_refusees_a_un_arbitre(client: AsyncClient, referee: User) -> None:
    token = await login(client, referee.email, REFEREE_PASSWORD)
    assert referee.referee_profile is not None
    referee_id = referee.referee_profile.id

    checks = [
        ("get", "/referees", None),
        ("post", "/referees/invite", INVITE),
        ("get", f"/referees/{referee_id}", None),
        ("patch", f"/referees/{referee_id}", {"city": "Tanger"}),
        ("post", f"/referees/{referee_id}/deactivate", None),
    ]
    for method, path, payload in checks:
        kwargs = {"headers": auth_header(token)}
        if payload is not None:
            kwargs["json"] = payload
        response = await getattr(client, method)(path, **kwargs)
        assert response.status_code == 403, f"{method.upper()} {path}"
        assert response.json()["code"] == "permission_denied"
