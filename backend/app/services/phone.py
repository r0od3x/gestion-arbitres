"""Normalisation et validation des numéros de téléphone en E.164."""

from __future__ import annotations

import phonenumbers

from app.core.config import settings
from app.services.errors import ValidationError


def normalize_phone(raw: str, region: str | None = None) -> str:
    """Convertit un numéro saisi librement en E.164 (ex. '06 12 34 56 78' → '+212612345678').

    Lève ValidationError si le numéro n'est pas un numéro valide.
    """
    candidate = (raw or "").strip()
    if not candidate:
        raise ValidationError("Le numéro de téléphone est vide.")

    try:
        parsed = phonenumbers.parse(candidate, region or settings.DEFAULT_PHONE_REGION)
    except phonenumbers.NumberParseException as exc:
        raise ValidationError(f"Numéro de téléphone illisible : {candidate!r}") from exc

    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError(f"Numéro de téléphone invalide : {candidate!r}")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def is_valid_e164(value: str) -> bool:
    try:
        return normalize_phone(value) == value
    except ValidationError:
        return False
