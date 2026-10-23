"""Hachage des mots de passe et émission/vérification des jetons JWT."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

TokenType = Literal["access", "refresh", "invite"]

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return True


def needs_rehash(password_hash: str) -> bool:
    """Vrai si le hash utilise des paramètres argon2 obsolètes."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


class TokenError(Exception):
    """Jeton absent, expiré, mal signé ou d'un type inattendu."""


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    return _create_token(
        str(user_id),
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES),
        {"role": role},
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(str(user_id), "refresh", timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS))


def create_invite_token(user_id: uuid.UUID, email: str) -> str:
    return _create_token(
        str(user_id),
        "invite",
        timedelta(hours=settings.INVITE_TOKEN_TTL_HOURS),
        {"email": email},
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Décode un jeton et vérifie son type. Lève TokenError si invalide."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"type de jeton inattendu: {payload.get('type')!r}")
    try:
        uuid.UUID(str(payload.get("sub")))
    except ValueError as exc:
        raise TokenError("sujet du jeton invalide") from exc
    return payload
