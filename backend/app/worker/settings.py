"""Point d'entrée du worker : `arq app.worker.settings.WorkerSettings`."""

from __future__ import annotations

from typing import Any, ClassVar

from app.core.config import settings
from app.core.logging import setup_logging
from app.notifications.factory import build_provider
from app.worker.queue import redis_settings
from app.worker.tasks import send_notification


async def startup(ctx: dict[str, Any]) -> None:
    setup_logging(settings.DEBUG)
    # Un seul fournisseur (et donc un seul client HTTP) pour tout le worker.
    ctx["provider"] = build_provider()


async def shutdown(ctx: dict[str, Any]) -> None:
    provider = ctx.get("provider")
    if provider is not None:
        await provider.close()


class WorkerSettings:
    functions: ClassVar[list[Any]] = [send_notification]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings()
    max_tries = settings.NOTIFICATION_MAX_ATTEMPTS
    #: Backoff exponentiel entre les tentatives (secondes).
    retry_delay = 30
    job_timeout = 60
    keep_result = 3600
