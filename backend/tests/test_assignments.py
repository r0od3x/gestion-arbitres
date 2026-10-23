"""Désignations : mise à jour différentielle et réponse de l'arbitre."""

from datetime import date, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import (
    AssignmentStatus,
    RefereeGrade,
    RefereeProfile,
    TournamentAssignment,
    TournamentStatus,
    User,
    UserRole,
)
from tests.conftest import ADMIN_PASSWORD, REFEREE_PASSWORD, auth_header, login
from tests.test_tournaments import make_tournament

PAST = date.today() - timedelta(days=30)


async def make_referee(
    session: AsyncSession,
    *,
    email: str,
    first: str = "Arbitre",
    last: str = "Test",
    phone: str | None = None,
    active: bool = True,
    opt_in: bool = True,
) -> RefereeProfile:
    user = User(
        email=email,
        password_hash=hash_password(REFEREE_PASSWORD),
        role=UserRole.REFEREE,
        is_active=active,
    )
    user.referee_profile = RefereeProfile(
        first_name=first,
        last_name=last,
        phone_e164=phone,
        grade=RefereeGrade.REGIONAL,
        whatsapp_opt_in=opt_in and phone is not None,
    )
    session.add(user)
    await session.commit()
    assert user.referee_profile is not None
    return user.referee_profile


async def admin_token(client: AsyncClient, admin: User) -> str:
    return await login(client, admin.email, ADMIN_PASSWORD)


# ----------------------------------------------------------------------
# Mise à jour différentielle
# ----------------------------------------------------------------------


async def test_premiere_designation_ajoute_tout(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin)
    a = await make_referee(session, email="a@test.ma", last="Alaoui", phone="+212612345601")
    b = await make_referee(session, email="b@test.ma", last="Bennis", phone="+212612345602")
    token = await admin_token(client, admin)

    response = await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id), str(b.id)]},
        headers=auth_header(token),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"added": 2, "cancelled": 0, "unchanged": 0}


async def test_le_differentiel_preserve_les_inchangees(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    """Le cœur de M3 : réenregistrer ne doit pas réinitialiser les réponses."""
    tournament = await make_tournament(session, admin, status=TournamentStatus.PUBLISHED)
    a = await make_referee(session, email="a@test.ma", last="Alaoui", phone="+212612345601")
    b = await make_referee(session, email="b@test.ma", last="Bennis", phone="+212612345602")
    c = await make_referee(session, email="c@test.ma", last="Chraibi", phone="+212612345603")
    token = await admin_token(client, admin)

    await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id), str(b.id)]},
        headers=auth_header(token),
    )

    # A confirme sa présence.
    arbitre_a = await login(client, "a@test.ma", REFEREE_PASSWORD)
    mes = await client.get("/me/assignments", headers=auth_header(arbitre_a))
    assignment_id = mes.json()[0]["id"]
    confirmed = await client.post(
        f"/me/assignments/{assignment_id}/confirm", headers=auth_header(arbitre_a)
    )
    assert confirmed.json()["status"] == AssignmentStatus.CONFIRMED.value

    # L'admin remplace B par C : A ne doit pas bouger.
    response = await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id), str(c.id)]},
        headers=auth_header(token),
    )
    assert response.json() == {"added": 1, "cancelled": 1, "unchanged": 1}

    listing = await client.get(
        f"/tournaments/{tournament.id}/assignments", headers=auth_header(token)
    )
    par_arbitre = {item["referee_id"]: item for item in listing.json()}
    assert par_arbitre[str(a.id)]["status"] == AssignmentStatus.CONFIRMED.value
    assert par_arbitre[str(a.id)]["responded_at"] is not None
    assert par_arbitre[str(c.id)]["status"] == AssignmentStatus.PENDING.value
    assert str(b.id) not in par_arbitre  # annulée, donc masquée par défaut


async def test_liste_vide_annule_tout(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin)
    a = await make_referee(session, email="a@test.ma", phone="+212612345601")
    token = await admin_token(client, admin)

    await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id)]},
        headers=auth_header(token),
    )
    response = await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": []},
        headers=auth_header(token),
    )

    assert response.json() == {"added": 0, "cancelled": 1, "unchanged": 0}


async def test_reconvoquer_apres_annulation_repart_en_attente(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin, status=TournamentStatus.PUBLISHED)
    a = await make_referee(session, email="a@test.ma", phone="+212612345601")
    token = await admin_token(client, admin)

    await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id)]},
        headers=auth_header(token),
    )
    arbitre = await login(client, "a@test.ma", REFEREE_PASSWORD)
    assignment_id = (await client.get("/me/assignments", headers=auth_header(arbitre))).json()[0][
        "id"
    ]
    await client.post(f"/me/assignments/{assignment_id}/decline", headers=auth_header(arbitre))

    # Retiré, puis remis.
    await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": []},
        headers=auth_header(token),
    )
    response = await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id)]},
        headers=auth_header(token),
    )

    assert response.json() == {"added": 1, "cancelled": 0, "unchanged": 0}
    listing = await client.get(
        f"/tournaments/{tournament.id}/assignments", headers=auth_header(token)
    )
    assert listing.json()[0]["status"] == AssignmentStatus.PENDING.value
    assert listing.json()[0]["responded_at"] is None


async def test_arbitre_en_double_refuse(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin)
    a = await make_referee(session, email="a@test.ma", phone="+212612345601")
    token = await admin_token(client, admin)

    response = await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id), str(a.id)]},
        headers=auth_header(token),
    )
    assert response.status_code == 422


async def test_arbitre_inconnu_refuse(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin)
    token = await admin_token(client, admin)

    response = await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": ["00000000-0000-0000-0000-000000000000"]},
        headers=auth_header(token),
    )
    assert response.status_code == 404


async def test_arbitre_desactive_non_convocable(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin)
    inactif = await make_referee(
        session, email="inactif@test.ma", last="Bennis", phone="+212612345604", active=False
    )
    token = await admin_token(client, admin)

    response = await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(inactif.id)]},
        headers=auth_header(token),
    )

    assert response.status_code == 422
    assert "désactivé" in response.json()["detail"]


async def test_pas_de_designation_sur_un_tournoi_annule(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin, status=TournamentStatus.CANCELLED)
    a = await make_referee(session, email="a@test.ma", phone="+212612345601")
    token = await admin_token(client, admin)

    response = await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id)]},
        headers=auth_header(token),
    )
    assert response.status_code == 409


async def test_la_liste_signale_qui_est_joignable(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    """L'admin doit voir avant l'envoi qui ne recevra pas de WhatsApp."""
    tournament = await make_tournament(session, admin)
    joignable = await make_referee(
        session, email="ok@test.ma", last="Alaoui", phone="+212612345601", opt_in=True
    )
    sans_consentement = await make_referee(
        session, email="ko@test.ma", last="Bennis", phone="+212612345602", opt_in=False
    )
    token = await admin_token(client, admin)

    await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(joignable.id), str(sans_consentement.id)]},
        headers=auth_header(token),
    )
    listing = await client.get(
        f"/tournaments/{tournament.id}/assignments", headers=auth_header(token)
    )

    par_arbitre = {item["referee_id"]: item for item in listing.json()}
    assert par_arbitre[str(joignable.id)]["is_notifiable"] is True
    assert par_arbitre[str(sans_consentement.id)]["is_notifiable"] is False
    # Aucune notification n'a encore été créée : ça, c'est M4.
    assert par_arbitre[str(joignable.id)]["notification_status"] is None


# ----------------------------------------------------------------------
# Réponse de l'arbitre
# ----------------------------------------------------------------------


async def test_confirmer_puis_changer_d_avis(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin, status=TournamentStatus.PUBLISHED)
    a = await make_referee(session, email="a@test.ma", phone="+212612345601")
    token = await admin_token(client, admin)
    await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id)]},
        headers=auth_header(token),
    )

    arbitre = await login(client, "a@test.ma", REFEREE_PASSWORD)
    assignment_id = (await client.get("/me/assignments", headers=auth_header(arbitre))).json()[0][
        "id"
    ]

    confirme = await client.post(
        f"/me/assignments/{assignment_id}/confirm", headers=auth_header(arbitre)
    )
    assert confirme.json()["status"] == AssignmentStatus.CONFIRMED.value

    decline = await client.post(
        f"/me/assignments/{assignment_id}/decline", headers=auth_header(arbitre)
    )
    assert decline.json()["status"] == AssignmentStatus.DECLINED.value


async def test_repondre_pour_un_autre_arbitre_refuse(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin, status=TournamentStatus.PUBLISHED)
    a = await make_referee(session, email="a@test.ma", last="Alaoui", phone="+212612345601")
    await make_referee(session, email="b@test.ma", last="Bennis", phone="+212612345602")
    token = await admin_token(client, admin)
    await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id)]},
        headers=auth_header(token),
    )

    arbitre_a = await login(client, "a@test.ma", REFEREE_PASSWORD)
    assignment_id = (await client.get("/me/assignments", headers=auth_header(arbitre_a))).json()[0][
        "id"
    ]

    arbitre_b = await login(client, "b@test.ma", REFEREE_PASSWORD)
    response = await client.post(
        f"/me/assignments/{assignment_id}/confirm", headers=auth_header(arbitre_b)
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


async def test_confirmer_un_tournoi_passe_refuse(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(
        session, admin, status=TournamentStatus.PUBLISHED, start=PAST
    )
    a = await make_referee(session, email="a@test.ma", phone="+212612345601")
    session.add(
        TournamentAssignment(
            tournament_id=tournament.id,
            referee_id=a.id,
            status=AssignmentStatus.PENDING,
            assigned_by=admin.id,
        )
    )
    await session.commit()

    arbitre = await login(client, "a@test.ma", REFEREE_PASSWORD)
    assignment_id = (await client.get("/me/assignments", headers=auth_header(arbitre))).json()[0][
        "id"
    ]

    response = await client.post(
        f"/me/assignments/{assignment_id}/confirm", headers=auth_header(arbitre)
    )

    assert response.status_code == 409
    assert "passé" in response.json()["detail"]


async def test_repondre_a_un_tournoi_annule_refuse(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin, status=TournamentStatus.PUBLISHED)
    a = await make_referee(session, email="a@test.ma", phone="+212612345601")
    token = await admin_token(client, admin)
    await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id)]},
        headers=auth_header(token),
    )
    arbitre = await login(client, "a@test.ma", REFEREE_PASSWORD)
    assignment_id = (await client.get("/me/assignments", headers=auth_header(arbitre))).json()[0][
        "id"
    ]

    await client.post(f"/tournaments/{tournament.id}/cancel", headers=auth_header(token))

    response = await client.post(
        f"/me/assignments/{assignment_id}/confirm", headers=auth_header(arbitre)
    )
    assert response.status_code == 409


async def test_mes_convocations_filtre_a_venir_et_passees(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    futur = await make_tournament(session, admin, title="Futur", status=TournamentStatus.PUBLISHED)
    passe = await make_tournament(
        session, admin, title="Passé", status=TournamentStatus.PUBLISHED, start=PAST
    )
    a = await make_referee(session, email="a@test.ma", phone="+212612345601")
    for tournament in (futur, passe):
        session.add(
            TournamentAssignment(
                tournament_id=tournament.id,
                referee_id=a.id,
                status=AssignmentStatus.PENDING,
                assigned_by=admin.id,
            )
        )
    await session.commit()

    arbitre = await login(client, "a@test.ma", REFEREE_PASSWORD)

    a_venir = await client.get("/me/assignments?upcoming=true", headers=auth_header(arbitre))
    passees = await client.get("/me/assignments?upcoming=false", headers=auth_header(arbitre))

    assert [item["tournament"]["title"] for item in a_venir.json()] == ["Futur"]
    assert [item["tournament"]["title"] for item in passees.json()] == ["Passé"]


async def test_un_arbitre_ne_voit_que_ses_convocations(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin, status=TournamentStatus.PUBLISHED)
    a = await make_referee(session, email="a@test.ma", last="Alaoui", phone="+212612345601")
    await make_referee(session, email="b@test.ma", last="Bennis", phone="+212612345602")
    token = await admin_token(client, admin)
    await client.put(
        f"/tournaments/{tournament.id}/assignments",
        json={"referee_ids": [str(a.id)]},
        headers=auth_header(token),
    )

    arbitre_b = await login(client, "b@test.ma", REFEREE_PASSWORD)
    response = await client.get("/me/assignments", headers=auth_header(arbitre_b))

    assert response.json() == []


async def test_convocations_refusees_a_un_anonyme(client: AsyncClient) -> None:
    assert (await client.get("/me/assignments")).status_code == 401
