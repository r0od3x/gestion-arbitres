"""Service d'authentification : connexion, rafraîchissement, acceptation d'invitation."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    TokenError,
    create_access_token,
    create_invite_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.db.base import utcnow
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.errors import AuthenticationError, ConflictError, ValidationError

logger = logging.getLogger(__name__)

#: Hash argon2 d'une valeur arbitraire, utilisé pour égaliser le temps de réponse
#: quand l'e-mail n'existe pas (évite l'énumération de comptes par timing).
_DUMMY_HASH = hash_password("mot-de-passe-factice-anti-timing")


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)

        if user is None or user.password_hash is None:
            # Même coût qu'une vérification réelle, puis même message d'erreur.
            verify_password(password, _DUMMY_HASH)
            raise AuthenticationError("E-mail ou mot de passe incorrect.")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("E-mail ou mot de passe incorrect.")

        if not user.is_active:
            raise AuthenticationError("Ce compte est désactivé.")

        # Ré-hachage transparent si les paramètres argon2 ont changé.
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        user.last_login_at = utcnow()
        await self.session.flush()
        return user

    def issue_tokens(self, user: User) -> tuple[str, str]:
        """Retourne (jeton d'accès, jeton de rafraîchissement)."""
        return create_access_token(user.id, user.role.value), create_refresh_token(user.id)

    async def user_from_refresh_token(self, token: str) -> User:
        try:
            payload = decode_token(token, "refresh")
        except TokenError as exc:
            logger.info("Jeton de rafraîchissement rejeté: %s", exc)
            raise AuthenticationError("Session expirée, reconnectez-vous.") from exc

        user = await self.users.get_with_profile(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise AuthenticationError("Session expirée, reconnectez-vous.")
        return user

    def create_invite_token(self, user: User) -> str:
        return create_invite_token(user.id, user.email)

    async def accept_invite(self, token: str, password: str) -> User:
        try:
            payload = decode_token(token, "invite")
        except TokenError as exc:
            raise ValidationError("Lien d'invitation invalide ou expiré.") from exc

        user = await self.users.get_with_profile(uuid.UUID(payload["sub"]))
        if user is None:
            raise ValidationError("Lien d'invitation invalide ou expiré.")
        if user.password_hash is not None:
            raise ConflictError("Cette invitation a déjà été utilisée.")

        user.password_hash = hash_password(password)
        user.is_active = True
        await self.session.flush()
        return user
