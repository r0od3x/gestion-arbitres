"""Tournois : création, modification, transitions de statut, visibilité."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Tournament, TournamentStatus, User
from tests.conftest import ADMIN_PASSWORD, REFEREE_PASSWORD, auth_header, login

TOMORROW = date.today() + timedelta(days=30)

NEW_TOURNAMENT = {
    "title": "Championnat régional",
    "city": "Casablanca",
    "start_date": TOMORROW.isoformat(),
    "end_date": (TOMORROW + timedelta(days=2)).isoformat(),
    "convocation_time": "08:30:00",
    "referees_needed": 4,
    "venue": "Complexe Mohammed V",
}


async def admin_token(client: AsyncClient, admin: User) -> str:
    return await login(client, admin.email, ADMIN_PASSWORD)


async def make_tournament(
    session: AsyncSession,
    admin: User,
    *,
    status: TournamentStatus = TournamentStatus.DRAFT,
    title: str = "Tournoi",
    city: str = "Casablanca",
    start: date | None = None,
    days: int = 2,
) -> Tournament:
    start = start or TOMORROW
    tournament = Tournament(
        title=title,
        city=city,
        start_date=start,
        end_date=start + timedelta(days=days),
        status=status,
        created_by=admin.id,
    )
    session.add(tournament)
    await session.commit()
    return tournament


# ----------------------------------------------------------------------
# Création et modification
# ----------------------------------------------------------------------


async def test_creation_demarre_en_brouillon(client: AsyncClient, admin: User) -> None:
    token = await admin_token(client, admin)

    response = await client.post("/tournaments", json=NEW_TOURNAMENT, headers=auth_header(token))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == TournamentStatus.DRAFT.value
    assert body["title"] == "Championnat régional"
    assert body["referees_needed"] == 4


async def test_date_de_fin_avant_debut_refusee(client: AsyncClient, admin: User) -> None:
    token = await admin_token(client, admin)

    response = await client.post(
        "/tournaments",
        json={**NEW_TOURNAMENT, "end_date": (TOMORROW - timedelta(days=1)).isoformat()},
        headers=auth_header(token),
    )
    assert response.status_code == 422


async def test_effectif_nul_refuse(client: AsyncClient, admin: User) -> None:
    token = await admin_token(client, admin)

    response = await client.post(
        "/tournaments",
        json={**NEW_TOURNAMENT, "referees_needed": 0},
        headers=auth_header(token),
    )
    assert response.status_code == 422


async def test_modification_partielle(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin)
    token = await admin_token(client, admin)

    response = await client.patch(
        f"/tournaments/{tournament.id}",
        json={"city": "Rabat"},
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert response.json()["city"] == "Rabat"
    assert response.json()["title"] == "Tournoi"  # inchangé


async def test_modification_incoherente_des_dates_refusee(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    """Chaque date peut bouger seule : le couple final doit rester cohérent."""
    tournament = await make_tournament(session, admin)
    token = await admin_token(client, admin)

    response = await client.patch(
        f"/tournaments/{tournament.id}",
        json={"end_date": (TOMORROW - timedelta(days=5)).isoformat()},
        headers=auth_header(token),
    )
    assert response.status_code == 422


async def test_modification_d_un_tournoi_annule_refusee(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin, status=TournamentStatus.CANCELLED)
    token = await admin_token(client, admin)

    response = await client.patch(
        f"/tournaments/{tournament.id}", json={"city": "Rabat"}, headers=auth_header(token)
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_state"


# ----------------------------------------------------------------------
# Transitions de statut
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("depart", "action", "arrivee"),
    [
        (TournamentStatus.DRAFT, "publish", TournamentStatus.PUBLISHED),
        (TournamentStatus.DRAFT, "cancel", TournamentStatus.CANCELLED),
        (TournamentStatus.PUBLISHED, "cancel", TournamentStatus.CANCELLED),
        (TournamentStatus.PUBLISHED, "complete", TournamentStatus.COMPLETED),
    ],
)
async def test_transitions_autorisees(
    client: AsyncClient,
    admin: User,
    session: AsyncSession,
    depart: TournamentStatus,
    action: str,
    arrivee: TournamentStatus,
) -> None:
    tournament = await make_tournament(session, admin, status=depart)
    token = await admin_token(client, admin)

    response = await client.post(
        f"/tournaments/{tournament.id}/{action}", headers=auth_header(token)
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == arrivee.value


@pytest.mark.parametrize(
    ("depart", "action"),
    [
        (TournamentStatus.DRAFT, "complete"),  # on ne clôture pas un brouillon
        (TournamentStatus.CANCELLED, "publish"),
        (TournamentStatus.CANCELLED, "complete"),
        (TournamentStatus.COMPLETED, "publish"),
        (TournamentStatus.COMPLETED, "cancel"),
        (TournamentStatus.PUBLISHED, "publish"),  # déjà dans cet état
    ],
)
async def test_transitions_interdites(
    client: AsyncClient,
    admin: User,
    session: AsyncSession,
    depart: TournamentStatus,
    action: str,
) -> None:
    tournament = await make_tournament(session, admin, status=depart)
    token = await admin_token(client, admin)

    response = await client.post(
        f"/tournaments/{tournament.id}/{action}", headers=auth_header(token)
    )

    assert response.status_code == 409, f"{depart} -> {action}"
    assert response.json()["code"] == "invalid_state"


# ----------------------------------------------------------------------
# Liste, filtres et visibilité
# ----------------------------------------------------------------------


async def test_liste_admin_voit_les_brouillons(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    await make_tournament(session, admin, status=TournamentStatus.DRAFT, title="Brouillon")
    await make_tournament(session, admin, status=TournamentStatus.PUBLISHED, title="Publié")
    token = await admin_token(client, admin)

    response = await client.get("/tournaments", headers=auth_header(token))

    assert response.json()["total"] == 2


async def test_un_arbitre_ne_voit_pas_les_brouillons(
    client: AsyncClient, admin: User, referee: User, session: AsyncSession
) -> None:
    await make_tournament(session, admin, status=TournamentStatus.DRAFT, title="Brouillon")
    await make_tournament(session, admin, status=TournamentStatus.PUBLISHED, title="Publié")
    token = await login(client, referee.email, REFEREE_PASSWORD)

    response = await client.get("/tournaments", headers=auth_header(token))

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Publié"


async def test_un_arbitre_ne_peut_pas_consulter_un_brouillon(
    client: AsyncClient, admin: User, referee: User, session: AsyncSession
) -> None:
    """404 plutôt que 403 : un brouillon n'existe pas de son point de vue."""
    tournament = await make_tournament(session, admin, status=TournamentStatus.DRAFT)
    token = await login(client, referee.email, REFEREE_PASSWORD)

    response = await client.get(f"/tournaments/{tournament.id}", headers=auth_header(token))

    assert response.status_code == 404


async def test_filtre_a_venir_et_passes(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    await make_tournament(session, admin, title="Futur", start=date.today() + timedelta(days=10))
    await make_tournament(session, admin, title="Passé", start=date.today() - timedelta(days=30))
    token = await admin_token(client, admin)

    futurs = await client.get("/tournaments?upcoming=true", headers=auth_header(token))
    passes = await client.get("/tournaments?upcoming=false", headers=auth_header(token))

    assert [t["title"] for t in futurs.json()["items"]] == ["Futur"]
    assert [t["title"] for t in passes.json()["items"]] == ["Passé"]


async def test_filtre_par_statut_et_recherche(
    client: AsyncClient, admin: User, session: AsyncSession
) -> None:
    await make_tournament(session, admin, status=TournamentStatus.PUBLISHED, title="Coupe du Roi")
    await make_tournament(session, admin, status=TournamentStatus.DRAFT, title="Tournoi local")
    token = await admin_token(client, admin)

    publies = await client.get("/tournaments?status=published", headers=auth_header(token))
    assert publies.json()["total"] == 1

    recherche = await client.get("/tournaments?q=coupe", headers=auth_header(token))
    assert recherche.json()["total"] == 1


# ----------------------------------------------------------------------
# Autorisation
# ----------------------------------------------------------------------


async def test_ecriture_refusee_a_un_arbitre(
    client: AsyncClient, admin: User, referee: User, session: AsyncSession
) -> None:
    tournament = await make_tournament(session, admin)
    token = await login(client, referee.email, REFEREE_PASSWORD)

    checks = [
        ("post", "/tournaments", NEW_TOURNAMENT),
        ("patch", f"/tournaments/{tournament.id}", {"city": "Rabat"}),
        ("post", f"/tournaments/{tournament.id}/publish", None),
        ("post", f"/tournaments/{tournament.id}/cancel", None),
        ("post", f"/tournaments/{tournament.id}/complete", None),
        ("get", f"/tournaments/{tournament.id}/assignments", None),
    ]
    for method, path, payload in checks:
        kwargs: dict[str, object] = {"headers": auth_header(token)}
        if payload is not None:
            kwargs["json"] = payload
        response = await getattr(client, method)(path, **kwargs)
        assert response.status_code == 403, f"{method.upper()} {path}"


async def test_routes_refusees_a_un_anonyme(client: AsyncClient) -> None:
    for method, path in [("get", "/tournaments"), ("post", "/tournaments")]:
        response = await getattr(client, method)(path)
        assert response.status_code == 401, path
