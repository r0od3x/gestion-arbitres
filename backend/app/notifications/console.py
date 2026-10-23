"""Fournisseur de développement : journalise au lieu d'envoyer. Utilisé en tests."""

from __future__ import annotations

import logging
import uuid

from app.notifications.base import NotificationProvider, OutboundMessage, SendResult

logger = logging.getLogger(__name__)


class ConsoleProvider(NotificationProvider):
    name = "console"

    def __init__(self) -> None:
        #: Messages envoyés, dans l'ordre — pratique pour les assertions de test.
        self.sent: list[OutboundMessage] = []

    async def send(self, message: OutboundMessage) -> SendResult:
        self.sent.append(message)
        logger.info(
            "[console] → %s | template=%s | variables=%s",
            message.to_phone_e164,
            message.template_name,
            message.variables,
        )
        return SendResult.ok(f"console-{uuid.uuid4()}")
