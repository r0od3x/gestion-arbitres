"""Fournisseur Meta WhatsApp Cloud API.

Les messages à l'initiative de l'entreprise doivent utiliser un template approuvé ;
le texte libre n'est autorisé que dans les 24 h suivant un message de l'utilisateur.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.notifications.base import NotificationProvider, OutboundMessage, SendResult

logger = logging.getLogger(__name__)

#: 4xx = erreur de configuration ou de données : relancer ne sert à rien.
#: 408/429 font exception (temporaires).
_RETRYABLE_4XX = {408, 429}


class WhatsAppCloudProvider(NotificationProvider):
    name = "whatsapp_cloud"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        if not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_ACCESS_TOKEN:
            raise RuntimeError(
                "WHATSAPP_PHONE_NUMBER_ID et WHATSAPP_ACCESS_TOKEN sont requis "
                "pour NOTIFICATION_PROVIDER=whatsapp_cloud."
            )
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(15.0))
        self._url = (
            f"{settings.WHATSAPP_API_BASE_URL.rstrip('/')}"
            f"/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )

    def _build_body(self, message: OutboundMessage) -> dict[str, Any]:
        components: list[dict[str, Any]] = []
        if message.variables:
            components.append(
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": value} for value in message.variables],
                }
            )
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            # L'API attend le numéro sans le '+'.
            "to": message.to_phone_e164.lstrip("+"),
            "type": "template",
            "template": {
                "name": message.template_name,
                "language": {"code": message.language_code},
                "components": components,
            },
        }

    async def send(self, message: OutboundMessage) -> SendResult:
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
        try:
            response = await self._client.post(
                self._url, json=self._build_body(message), headers=headers
            )
        except httpx.RequestError as exc:
            # Panne réseau : temporaire par nature.
            logger.warning("WhatsApp injoignable: %s", exc.__class__.__name__)
            return SendResult.failure(f"Erreur réseau: {exc}", retryable=True)

        if response.is_success:
            data = response.json()
            try:
                message_id = data["messages"][0]["id"]
            except (KeyError, IndexError, TypeError):
                return SendResult.failure(
                    "Réponse WhatsApp inattendue (identifiant de message absent)."
                )
            return SendResult.ok(message_id, raw=data)

        retryable = response.status_code >= 500 or response.status_code in _RETRYABLE_4XX
        detail = _extract_error(response)
        logger.warning(
            "Envoi WhatsApp refusé (HTTP %s, relançable=%s): %s",
            response.status_code,
            retryable,
            detail,
        )
        return SendResult.failure(f"HTTP {response.status_code}: {detail}", retryable=retryable)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _extract_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300]
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        parts = [
            str(error.get("message", "")),
            str(error.get("error_user_msg") or ""),
            f"code={error.get('code')}" if error.get("code") is not None else "",
        ]
        return " | ".join(part for part in parts if part)[:300]
    return str(payload)[:300]


def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Vérifie l'en-tête `X-Hub-Signature-256` envoyé par Meta."""
    if not settings.WHATSAPP_APP_SECRET:
        logger.error("WHATSAPP_APP_SECRET absent : webhook rejeté.")
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(settings.WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.removeprefix("sha256="))
