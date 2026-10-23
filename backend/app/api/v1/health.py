"""Sondes de santé : `/healthz` (process) et `/readyz` (dépendances)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="L'application répond")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@router.get("/readyz", summary="L'application et ses dépendances sont prêtes")
async def readyz(session: DbSession, response: Response) -> dict[str, Any]:
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # on rapporte l'état, on ne propage pas
        checks["database"] = f"error: {exc.__class__.__name__}"

    ready = all(value == "ok" for value in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready else "degraded", "checks": checks}
