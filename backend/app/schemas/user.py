"""Schémas utilisateur et profil arbitre."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import RefereeGrade, UserRole


class RefereeProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    phone_e164: str | None
    whatsapp_opt_in: bool
    whatsapp_opt_in_at: datetime | None
    grade: RefereeGrade
    license_number: str | None
    city: str | None
    club: str | None
    league: str | None
    photo_url: str | None


class RefereeProfileAdminRead(RefereeProfileRead):
    """Vue administrateur : ajoute les champs réservés aux admins."""

    notes_admin: str | None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class MeRead(UserRead):
    referee_profile: RefereeProfileRead | None = None


class RefereeProfileUpdate(BaseModel):
    """Champs qu'un arbitre peut modifier lui-même."""

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(
        default=None, description="Numéro local ou international, normalisé en E.164"
    )
    whatsapp_opt_in: bool | None = None
    city: str | None = Field(default=None, max_length=100)
    club: str | None = Field(default=None, max_length=150)
    league: str | None = Field(default=None, max_length=150)
