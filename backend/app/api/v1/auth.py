"""Routes d'authentification.

Le jeton d'accès est renvoyé dans le corps (stocké en mémoire côté SPA) ;
le jeton de rafraîchissement part en cookie httpOnly, jamais lisible en JS.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import CurrentUser, DbSession, client_ip
from app.core.config import settings
from app.core.ratelimit import login_limiter
from app.schemas.auth import AcceptInviteRequest, LoginRequest, TokenResponse
from app.schemas.common import Message
from app.schemas.user import MeRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 24 * 3600,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/api/v1/auth",
    )


def _token_response(access_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_TTL_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse, summary="Se connecter")
async def login(
    payload: LoginRequest,
    response: Response,
    session: DbSession,
    ip: str = Depends(client_ip),
) -> TokenResponse:
    login_limiter.check(ip)

    service = AuthService(session)
    user = await service.authenticate(payload.email, payload.password)
    access_token, refresh_token = service.issue_tokens(user)

    _set_refresh_cookie(response, refresh_token)
    return _token_response(access_token)


@router.post("/refresh", response_model=TokenResponse, summary="Renouveler le jeton d'accès")
async def refresh(
    request: Request,
    response: Response,
    session: DbSession,
) -> TokenResponse:
    service = AuthService(session)
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME) or ""
    user = await service.user_from_refresh_token(token)

    access_token, refresh_token = service.issue_tokens(user)
    # Rotation : chaque rafraîchissement remplace le cookie précédent.
    _set_refresh_cookie(response, refresh_token)
    return _token_response(access_token)


@router.post("/logout", response_model=Message, summary="Se déconnecter")
async def logout(response: Response) -> Message:
    _clear_refresh_cookie(response)
    return Message(detail="Déconnecté.")


@router.post(
    "/accept-invite",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Définir son mot de passe depuis un lien d'invitation",
)
async def accept_invite(
    payload: AcceptInviteRequest,
    response: Response,
    session: DbSession,
) -> TokenResponse:
    service = AuthService(session)
    user = await service.accept_invite(payload.token, payload.password)

    access_token, refresh_token = service.issue_tokens(user)
    _set_refresh_cookie(response, refresh_token)
    return _token_response(access_token)


@router.get("/me", response_model=MeRead, summary="Utilisateur connecté")
async def read_me(user: CurrentUser) -> MeRead:
    return MeRead.model_validate(user)
