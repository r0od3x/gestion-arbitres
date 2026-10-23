"""Tâches ARQ exécutées hors du cycle requête/réponse."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.db.session import SessionFactory
from app.services.errors import NotFoundError
from app.services.notifications import NotificationService

logger = logging.getLogger(__name__)


async def send_notification(ctx: dict[str, Any], notification_id: str) -> str:
    """Envoie une notification. Relancée par ARQ si elle reste `queued`."""
    async with SessionFactory() as session:
        service = NotificationService(session, provider=ctx.get("provider"))
        try:
            notification = await service.deliver(uuid.UUID(notification_id))
        except NotFoundError:
            logger.warning("Job ignoré, notification %s supprimée", notification_id)
            await session.rollback()
            return "not_found"
        await session.commit()

    logger.info(
        "Notification %s traitée: statut=%s tentatives=%s",
        notification_id,
        notification.status,
        notification.attempts,
    )
    return notification.status.value
