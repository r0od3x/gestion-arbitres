"""Erreurs métier. Les routers les traduisent en réponses HTTP (voir app/main.py)."""

from __future__ import annotations


class DomainError(Exception):
    """Erreur métier. `status_code` sert au gestionnaire d'exceptions HTTP."""

    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class ValidationError(DomainError):
    status_code = 422
    code = "validation_error"


class AuthenticationError(DomainError):
    status_code = 401
    code = "authentication_failed"


class PermissionDeniedError(DomainError):
    status_code = 403
    code = "permission_denied"


class InvalidStateError(DomainError):
    """Transition interdite, ex. convoquer sur un tournoi annulé."""

    status_code = 409
    code = "invalid_state"
