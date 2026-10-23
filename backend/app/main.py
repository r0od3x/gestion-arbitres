"""Fabrique de l'application FastAPI."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.session import engine
from app.services.errors import DomainError

logger = logging.getLogger(__name__)

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.DEBUG)
    logger.info(
        "Démarrage de l'API (env=%s, provider=%s)",
        settings.ENVIRONMENT,
        settings.NOTIFICATION_PROVIDER,
    )
    yield
    await engine.dispose()
    logger.info("Arrêt de l'API")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Gestion des Arbitres — API",
        description="Convocation des arbitres aux tournois et notifications WhatsApp.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,  # nécessaire pour le cookie de rafraîchissement
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        """Traduit les erreurs métier en réponses HTTP cohérentes."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
            headers=({"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None),
        )

    app.include_router(api_router, prefix=API_V1_PREFIX)
    return app


app = create_app()
