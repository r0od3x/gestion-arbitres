"""Interface commune aux fournisseurs de notification."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class OutboundMessage:
    """Message à envoyer, indépendant du fournisseur."""

    to_phone_e164: str
    template_name: str
    #: Variables positionnelles du template : {{1}}, {{2}}, … dans l'ordre.
    variables: list[str] = field(default_factory=list)
    language_code: str = "fr"


@dataclass(slots=True)
class SendResult:
    """Résultat d'un envoi. `retryable` pilote la relance par le worker."""

    success: bool
    provider_message_id: str | None = None
    error: str | None = None
    retryable: bool = False
    raw_response: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, message_id: str, raw: dict[str, Any] | None = None) -> SendResult:
        return cls(success=True, provider_message_id=message_id, raw_response=raw or {})

    @classmethod
    def failure(cls, error: str, *, retryable: bool = False) -> SendResult:
        return cls(success=False, error=error, retryable=retryable)


class NotificationProvider(ABC):
    """Un canal d'envoi concret (WhatsApp Cloud, Twilio, console…)."""

    name: str

    @abstractmethod
    async def send(self, message: OutboundMessage) -> SendResult:
        """Envoie le message. Ne lève pas : les échecs sont retournés en SendResult."""

    async def close(self) -> None:
        """Libère les ressources (client HTTP, etc.)."""
        return None
