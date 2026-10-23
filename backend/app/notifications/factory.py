"""Sélection du fournisseur de notification depuis la configuration."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import NotificationProviderName, settings
from app.notifications.base import NotificationProvider
from app.notifications.console import ConsoleProvider


def build_provider(name: NotificationProviderName | None = None) -> NotificationProvider:
    provider_name = name or settings.NOTIFICATION_PROVIDER

    if provider_name == "console":
        return ConsoleProvider()
    if provider_name == "whatsapp_cloud":
        from app.notifications.whatsapp_cloud import WhatsAppCloudProvider

        return WhatsAppCloudProvider()
    if provider_name == "twilio":  # pragma: no cover - prévu en phase 2
        raise NotImplementedError("Le fournisseur Twilio n'est pas encore implémenté.")

    raise ValueError(f"Fournisseur de notification inconnu: {provider_name!r}")


@lru_cache
def get_provider() -> NotificationProvider:
    """Instance partagée (le client HTTP est réutilisé entre les envois)."""
    return build_provider()
