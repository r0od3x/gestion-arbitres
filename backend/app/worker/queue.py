"""Mise en file des jobs depuis l'API."""

from __future__ import annotations

import logging
import uuid

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)

SEND_NOTIFICATION_TASK = "send_notification"


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.REDIS_URL)


async def get_queue() -> ArqRedis:
    return await create_pool(redis_settings())


async def enqueue_notification(queue: ArqRedis, notification_id: uuid.UUID) -> None:
    """Met en file l'envoi d'une notification.

    `_job_id` rend l'opération idempotente : réenfiler la même notification
    ne crée pas de doublon tant que le job n'est pas terminé.
    """
    await queue.enqueue_job(
        SEND_NOTIFICATION_TASK,
        str(notification_id),
        _job_id=f"notification:{notification_id}",
    )
