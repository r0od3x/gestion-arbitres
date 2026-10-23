"""Agrégation des routes de l'API v1."""

from fastapi import APIRouter

from app.api.v1 import auth, health, me, referees

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(referees.router)

# Ajoutés au fil des jalons :
#   M3 — tournaments, assignments
#   M4 — webhooks
