"""Amorçage de la base : premier administrateur et, en option, un jeu de démonstration.

Usage :
    python -m scripts.seed              # administrateur seul
    python -m scripts.seed --demo       # + arbitres et tournoi de démonstration
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.security import hash_password
from app.db.base import utcnow
from app.db.session import SessionFactory, engine
from app.models import (
    RefereeGrade,
    RefereeProfile,
    Tournament,
    TournamentStatus,
    User,
    UserRole,
)
from app.repositories.user import UserRepository

logger = logging.getLogger("seed")

DEMO_REFEREES = [
    ("Youssef", "El Amrani", "+212612345671", "Casablanca", RefereeGrade.NATIONAL, "ARB-001"),
    ("Salma", "Benali", "+212612345672", "Rabat", RefereeGrade.REGIONAL, "ARB-002"),
    ("Karim", "Ouazzani", "+212612345673", "Marrakech", RefereeGrade.INTERNATIONAL, "ARB-003"),
    ("Nadia", "Tazi", "+212612345674", "Casablanca", RefereeGrade.CONTINENTAL, "ARB-004"),
]


async def ensure_admin(session: AsyncSession) -> User:
    users = UserRepository(session)
    existing = await users.get_by_email(settings.FIRST_ADMIN_EMAIL)
    if existing is not None:
        logger.info("Administrateur déjà présent: %s", existing.email)
        return existing

    admin = User(
        email=settings.FIRST_ADMIN_EMAIL.strip().lower(),
        password_hash=hash_password(settings.FIRST_ADMIN_PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(admin)
    await session.flush()
    logger.info("Administrateur créé: %s", admin.email)
    return admin


async def seed_demo(session: AsyncSession, admin: User) -> None:
    users = UserRepository(session)

    for first, last, phone, city, grade, license_number in DEMO_REFEREES:
        email = f"{first}.{last}@example.ma".lower().replace(" ", "")
        if await users.email_exists(email):
            continue

        user = User(
            email=email,
            password_hash=hash_password("Arbitre!2026"),
            role=UserRole.REFEREE,
            is_active=True,
        )
        user.referee_profile = RefereeProfile(
            first_name=first,
            last_name=last,
            phone_e164=phone,
            city=city,
            grade=grade,
            license_number=license_number,
            whatsapp_opt_in=True,
            whatsapp_opt_in_at=utcnow(),
        )
        session.add(user)
        logger.info("Arbitre de démonstration: %s %s", first, last)

    start = date.today() + timedelta(days=21)
    session.add(
        Tournament(
            title="Championnat régional — Casablanca",
            description="Tournoi de démonstration créé par le script d'amorçage.",
            venue="Complexe sportif Mohammed V",
            city="Casablanca",
            start_date=start,
            end_date=start + timedelta(days=2),
            convocation_time=time(8, 30),
            referees_needed=4,
            status=TournamentStatus.DRAFT,
            created_by=admin.id,
        )
    )
    await session.flush()


async def main(demo: bool) -> None:
    setup_logging()
    async with SessionFactory() as session:
        admin = await ensure_admin(session)
        if demo:
            await seed_demo(session, admin)
        await session.commit()
    await engine.dispose()
    logger.info("Amorçage terminé.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amorce la base de données.")
    parser.add_argument(
        "--demo", action="store_true", help="Ajoute des arbitres et un tournoi de démo."
    )
    args = parser.parse_args()
    asyncio.run(main(demo=args.demo))
