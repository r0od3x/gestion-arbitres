"""Agrégation des routes de l'API v1."""

from fastapi import APIRouter

from app.api.v1 import auth, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)

# Ajoutés au fil des jalons :
#   M2 — referees
#   M3 — tournaments, assignments, me
#   M4 — webhooks
