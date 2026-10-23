"""Dépendances FastAPI : session, utilisateur courant, contrôle des rôles.

L'autorisation vit ici et nulle part ailleurs : chaque route protégée déclare
`CurrentUser`, `AdminUser` ou `RefereeUser`.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenError, decode_token
from app.db.session import get_session
from app.models.referee import RefereeProfile
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.errors import AuthenticationError, PermissionDeniedError

_bearer = HTTPBearer(auto_error=False, description="Jeton d'accès JWT")


async def get_db(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncGenerator[AsyncSession, None]:
    """Session transactionnelle : commit si la route réussit, rollback sinon."""
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DbSession,
) -> User:
    if credentials is None:
        raise AuthenticationError("Authentification requise.")

    try:
        payload = decode_token(credentials.credentials, "access")
    except TokenError as exc:
        raise AuthenticationError("Jeton d'accès invalide ou expiré.") from exc

    user = await UserRepository(session).get_with_profile(uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthenticationError("Compte introuvable ou désactivé.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        raise PermissionDeniedError("Accès réservé aux administrateurs.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


async def require_referee_profile(user: CurrentUser) -> RefereeProfile:
    """Garantit que l'appelant est un arbitre disposant d'un profil."""
    if user.is_admin or user.referee_profile is None:
        raise PermissionDeniedError("Accès réservé aux arbitres.")
    return user.referee_profile


RefereeUser = Annotated[RefereeProfile, Depends(require_referee_profile)]


def client_ip(request: Request) -> str:
    """IP de l'appelant, en tenant compte d'un éventuel reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
