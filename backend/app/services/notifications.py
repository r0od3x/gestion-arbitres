"""Cycle de vie d'une notification : construction, envoi, suivi de livraison.

L'API n'envoie jamais : elle crée une ligne `notifications` à l'état `queued`
et met un job en file. Ce service est appelé par le worker.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import utcnow
from app.models.enums import (
    NOTIFICATION_STATUS_RANK,
    TERMINAL_NOTIFICATION_STATUSES,
    NotificationStatus,
)
from app.models.notification import Notification
from app.notifications.base import NotificationProvider, OutboundMessage
from app.notifications.factory import get_provider
from app.services.errors import NotFoundError

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, session: AsyncSession, provider: NotificationProvider | None = None) -> None:
        self.session = session
        self._provider = provider

    @property
    def provider(self) -> NotificationProvider:
        if self._provider is None:
            self._provider = get_provider()
        return self._provider

    @staticmethod
    def build_message(notification: Notification) -> OutboundMessage:
        """Reconstruit le message à partir du payload stocké."""
        payload: dict[str, Any] = notification.payload or {}
        raw_variables = payload.get("variables", [])
        return OutboundMessage(
            to_phone_e164=notification.recipient_phone_e164,
            template_name=notification.template_name,
            variables=[str(value) for value in raw_variables],
            language_code=str(payload.get("language_code", "fr")),
        )

    async def deliver(self, notification_id: uuid.UUID) -> Notification:
        """Envoie une notification et met son statut à jour. Idempotent."""
        notification = await self.session.get(Notification, notification_id)
        if notification is None:
            raise NotFoundError(f"Notification {notification_id} introuvable.")

        if notification.status in TERMINAL_NOTIFICATION_STATUSES or (
            notification.status is not NotificationStatus.QUEUED
        ):
            # Déjà envoyée (ou déjà en échec définitif) : ne pas renvoyer.
            logger.info("Notification %s ignorée (statut=%s)", notification_id, notification.status)
            return notification

        notification.attempts += 1
        result = await self.provider.send(self.build_message(notification))

        if result.success:
            notification.status = NotificationStatus.SENT
            notification.provider_message_id = result.provider_message_id
            notification.sent_at = utcnow()
            notification.error = None
        elif result.retryable and notification.attempts < settings.NOTIFICATION_MAX_ATTEMPTS:
            # Reste `queued` : ARQ relancera le job.
            notification.error = result.error
            logger.warning(
                "Envoi %s échoué (tentative %s/%s), relance prévue",
                notification_id,
                notification.attempts,
                settings.NOTIFICATION_MAX_ATTEMPTS,
            )
        else:
            notification.status = NotificationStatus.FAILED
            notification.error = result.error

        await self.session.flush()
        return notification

    async def apply_provider_status(
        self,
        provider_message_id: str,
        new_status: NotificationStatus,
        error: str | None = None,
    ) -> Notification | None:
        """Applique une mise à jour reçue par webhook.

        Les webhooks arrivent parfois dans le désordre : un statut moins avancé
        que celui déjà enregistré est ignoré.
        """
        statement = select(Notification).where(
            Notification.provider_message_id == provider_message_id
        )
        notification = await self.session.scalar(statement)
        if notification is None:
            logger.info("Webhook pour un message inconnu: %s", provider_message_id)
            return None

        current_rank = NOTIFICATION_STATUS_RANK[notification.status]
        if NOTIFICATION_STATUS_RANK[new_status] <= current_rank:
            return notification

        notification.status = new_status
        if error:
            notification.error = error
        await self.session.flush()
        return notification
