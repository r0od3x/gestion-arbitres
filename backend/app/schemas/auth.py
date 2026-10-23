"""Schémas d'authentification."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

Password = Annotated[
    str,
    Field(
        min_length=10,
        max_length=128,
        description="Au moins 10 caractères",
    ),
]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Le jeton de rafraîchissement n'est pas dans le corps : il est posé en cookie httpOnly."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Durée de vie du jeton d'accès, en secondes")


class AcceptInviteRequest(BaseModel):
    token: str = Field(min_length=1)
    password: Password
