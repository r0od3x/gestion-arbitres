"""Schémas des routes arbitres (espace administrateur)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import RefereeGrade
from app.models.referee import RefereeProfile
from app.schemas.user import RefereeProfileAdminRead


class RefereeInviteRequest(BaseModel):
    """Création d'un arbitre par un administrateur, avant acceptation."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(
        default=None, description="Numéro local ou international, normalisé en E.164"
    )
    grade: RefereeGrade = RefereeGrade.REGIONAL
    license_number: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, max_length=100)
    club: str | None = Field(default=None, max_length=150)
    league: str | None = Field(default=None, max_length=150)
    notes_admin: str | None = None


class RefereeAdminUpdate(BaseModel):
    """Champs qu'un administrateur peut modifier sur un arbitre.

    Tous optionnels : seuls les champs transmis sont appliqués. `extra="forbid"`
    évite qu'une faute de frappe passe inaperçue.
    """

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = None
    grade: RefereeGrade | None = None
    license_number: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, max_length=100)
    club: str | None = Field(default=None, max_length=150)
    league: str | None = Field(default=None, max_length=150)
    notes_admin: str | None = None
    whatsapp_opt_in: bool | None = None


class RefereeRead(RefereeProfileAdminRead):
    """Arbitre vu par un administrateur : profil + état du compte."""

    user_id: uuid.UUID
    email: EmailStr
    is_active: bool
    #: Faux tant que l'invitation n'a pas été acceptée.
    has_accepted_invite: bool
    created_at: datetime

    @classmethod
    def from_profile(cls, profile: RefereeProfile) -> RefereeRead:
        """Construit la vue à partir d'un profil et de son compte utilisateur."""
        return cls(
            id=profile.id,
            user_id=profile.user_id,
            email=profile.user.email,
            is_active=profile.user.is_active,
            has_accepted_invite=profile.user.has_accepted_invite,
            created_at=profile.created_at,
            first_name=profile.first_name,
            last_name=profile.last_name,
            phone_e164=profile.phone_e164,
            whatsapp_opt_in=profile.whatsapp_opt_in,
            whatsapp_opt_in_at=profile.whatsapp_opt_in_at,
            grade=profile.grade,
            license_number=profile.license_number,
            city=profile.city,
            club=profile.club,
            league=profile.league,
            photo_url=profile.photo_url,
            notes_admin=profile.notes_admin,
        )


class RefereeInviteResponse(BaseModel):
    """Arbitre créé, accompagné du lien d'invitation à lui transmettre."""

    referee: RefereeRead
    #: Lien vers le frontend ; l'envoi par e-mail viendra en phase 2.
    invite_url: str
    invite_expires_in_hours: int
