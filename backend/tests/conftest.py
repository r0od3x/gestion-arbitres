"""Fixtures de test.

Les variables d'environnement sont posées AVANT tout import de l'application :
`app.core.config.settings` est construit à l'import.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

_TEST_DB = Path(tempfile.mkdtemp(prefix="arbitres-tests-")) / "test.db"

os.environ.update(
    ENVIRONMENT="test",
    DATABASE_URL=f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}",
    JWT_SECRET="secret-de-test-ne-pas-utiliser-en-production",
    NOTIFICATION_PROVIDER="console",
    COOKIE_SECURE="false",
)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.core.ratelimit import login_limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import RefereeGrade, RefereeProfile, User, UserRole  # noqa: E402

ADMIN_PASSWORD = "AdminTest!2026"
REFEREE_PASSWORD = "ArbitreTest!2026"

test_engine = create_async_engine(os.environ["DATABASE_URL"])
TestSessionFactory = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@pytest.fixture(autouse=True)
async def _fresh_database() -> AsyncGenerator[None, None]:
    """Schéma recréé avant chaque test : isolation totale, pas d'ordre implicite."""
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    login_limiter.reset()
    yield


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionFactory() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def _override() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionFactory() as session:
            yield session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def admin(session: AsyncSession) -> User:
    user = User(
        email="admin@test.ma",
        password_hash=hash_password(ADMIN_PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    return user


@pytest.fixture
async def referee(session: AsyncSession) -> User:
    user = User(
        email="arbitre@test.ma",
        password_hash=hash_password(REFEREE_PASSWORD),
        role=UserRole.REFEREE,
        is_active=True,
    )
    user.referee_profile = RefereeProfile(
        first_name="Youssef",
        last_name="El Amrani",
        phone_e164="+212612345671",
        city="Casablanca",
        grade=RefereeGrade.NATIONAL,
        whatsapp_opt_in=True,
    )
    session.add(user)
    await session.commit()
    return user


async def login(client: AsyncClient, email: str, password: str) -> str:
    """Se connecte et retourne le jeton d'accès."""
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
