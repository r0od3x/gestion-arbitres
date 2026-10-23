"""Service arbitres : invitation, consultation, modification, désactivation.

Toutes les règles métier du jalon M2 vivent ici. Les routers se contentent de
traduire HTTP ↔ schémas, et les repositories de parler à la base.
"""

from __future__ import annotations

import logging
import uuid
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import utcnow
from app.models.enums import RefereeGrade, UserRole
from app.models.referee import RefereeProfile
from app.models.user import User
from app.repositories.referee import RefereeRepository
from app.repositories.user import UserRepository
from app.schemas.referee import RefereeAdminUpdate, RefereeInviteRequest
from app.schemas.user import RefereeProfileUpdate
from app.services.auth import AuthService
from app.services.errors import ConflictError, NotFoundError, ValidationError
from app.services.phone import normalize_phone

logger = logging.getLogger(__name__)


class RefereeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.referees = RefereeRepository(session)
        self.users = UserRepository(session)

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------

    async def get(self, referee_id: uuid.UUID) -> RefereeProfile:
        profile = await self.referees.get_with_user(referee_id)
        if profile is None:
            raise NotFoundError("Arbitre introuvable.")
        return profile

    async def search(
        self,
        *,
        grade: RefereeGrade | None = None,
        city: str | None = None,
        active: bool | None = None,
        query: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[RefereeProfile], int]:
        statement = self.referees.search_statement(
            grade=grade, city=city, active=active, query=query
        )
        return await self.referees.search_page(statement, page=page, size=size)

    # ------------------------------------------------------------------
    # Invitation
    # ------------------------------------------------------------------

    async def invite(self, payload: RefereeInviteRequest) -> tuple[RefereeProfile, str]:
        """Crée un compte arbitre sans mot de passe et retourne le lien d'invitation.

        Le compte est inutilisable tant que l'arbitre n'a pas accepté
        l'invitation : `password_hash` reste NULL (voir AuthService.authenticate).
        """
        email = payload.email.strip().lower()
        if await self.users.email_exists(email):
            raise ConflictError("Un compte existe déjà avec cette adresse e-mail.")

        phone_e164 = normalize_phone(payload.phone) if payload.phone else None
        if phone_e164 is not None:
            await self._ensure_phone_available(phone_e164)
        if payload.license_number:
            await self._ensure_license_available(payload.license_number)

        user = User(email=email, password_hash=None, role=UserRole.REFEREE, is_active=True)
        user.referee_profile = RefereeProfile(
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            phone_e164=phone_e164,
            grade=payload.grade,
            license_number=payload.license_number,
            city=payload.city,
            club=payload.club,
            league=payload.league,
            notes_admin=payload.notes_admin,
            # Le consentement WhatsApp appartient à l'arbitre : un administrateur
            # ne peut pas le donner à sa place (loi 09-08 / CNDP).
            whatsapp_opt_in=False,
        )
        self.session.add(user)
        await self.session.flush()

        invite_url = self.build_invite_url(user)
        logger.info("Invitation créée pour %s", email)
        assert user.referee_profile is not None
        return user.referee_profile, invite_url

    def build_invite_url(self, user: User) -> str:
        token = AuthService(self.session).create_invite_token(user)
        base = settings.FRONTEND_URL.rstrip("/")
        return f"{base}/invitation?token={quote(token)}"

    async def resend_invite(self, referee_id: uuid.UUID) -> str:
        """Régénère un lien d'invitation pour un arbitre qui n'a pas encore accepté."""
        profile = await self.get(referee_id)
        if profile.user.has_accepted_invite:
            raise ConflictError("Cet arbitre a déjà activé son compte.")
        return self.build_invite_url(profile.user)

    # ------------------------------------------------------------------
    # Modification
    # ------------------------------------------------------------------

    async def update_as_admin(
        self, referee_id: uuid.UUID, payload: RefereeAdminUpdate
    ) -> RefereeProfile:
        profile = await self.get(referee_id)
        changes = payload.model_dump(exclude_unset=True)
        await self._apply_changes(profile, changes)
        await self.session.flush()
        return profile

    async def update_own_profile(
        self, profile: RefereeProfile, payload: RefereeProfileUpdate
    ) -> RefereeProfile:
        """Mise à jour par l'arbitre lui-même.

        Le schéma `RefereeProfileUpdate` ne contient volontairement ni `grade`,
        ni `license_number`, ni `notes_admin` : un arbitre ne se promeut pas.
        """
        changes = payload.model_dump(exclude_unset=True)
        await self._apply_changes(profile, changes)
        await self.session.flush()
        return profile

    async def _apply_changes(self, profile: RefereeProfile, changes: dict[str, object]) -> None:
        if "phone" in changes:
            raw_phone = changes.pop("phone")
            phone_e164 = normalize_phone(str(raw_phone)) if raw_phone else None
            if phone_e164 != profile.phone_e164:
                if phone_e164 is not None:
                    await self._ensure_phone_available(phone_e164, exclude_id=profile.id)
                profile.phone_e164 = phone_e164

        if "license_number" in changes:
            license_number = changes.pop("license_number")
            value = str(license_number) if license_number else None
            if value != profile.license_number:
                if value is not None:
                    await self._ensure_license_available(value, exclude_id=profile.id)
                profile.license_number = value

        if "whatsapp_opt_in" in changes:
            self._set_consent(profile, bool(changes.pop("whatsapp_opt_in")))

        # Les champs restants sont de simples chaînes ou énumérations validées
        # par Pydantic : une affectation directe suffit.
        for field, new_value in changes.items():
            setattr(profile, field, new_value)

        # Un consentement sans numéro joignable n'a pas de sens.
        if profile.whatsapp_opt_in and not profile.phone_e164:
            raise ValidationError(
                "Un numéro de téléphone est nécessaire pour recevoir les convocations par WhatsApp."
            )

    @staticmethod
    def _set_consent(profile: RefereeProfile, opt_in: bool) -> None:
        """Horodate le consentement au moment où il est donné, et l'efface au retrait."""
        if opt_in == profile.whatsapp_opt_in:
            return
        profile.whatsapp_opt_in = opt_in
        profile.whatsapp_opt_in_at = utcnow() if opt_in else None

    # ------------------------------------------------------------------
    # Activation / désactivation
    # ------------------------------------------------------------------

    async def set_active(self, referee_id: uuid.UUID, active: bool) -> RefereeProfile:
        """Active ou désactive le compte. On ne supprime pas : l'historique des
        convocations doit rester intact."""
        profile = await self.get(referee_id)
        profile.user.is_active = active
        await self.session.flush()
        return profile

    # ------------------------------------------------------------------
    # Unicité
    # ------------------------------------------------------------------

    async def _ensure_phone_available(
        self, phone_e164: str, exclude_id: uuid.UUID | None = None
    ) -> None:
        existing = await self.referees.get_by_phone(phone_e164)
        if existing is not None and existing.id != exclude_id:
            raise ConflictError("Ce numéro de téléphone est déjà utilisé par un autre arbitre.")

    async def _ensure_license_available(
        self, license_number: str, exclude_id: uuid.UUID | None = None
    ) -> None:
        existing = await self.referees.get_by_license(license_number)
        if existing is not None and existing.id != exclude_id:
            raise ConflictError("Ce numéro de licence est déjà attribué.")
