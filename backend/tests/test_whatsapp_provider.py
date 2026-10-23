"""Fournisseur WhatsApp Cloud : construction de la requête, classement des erreurs,
et vérification de la signature des webhooks. Aucun appel réseau réel.
"""

import hashlib
import hmac
from collections.abc import Iterator

import httpx
import pytest

from app.core.config import settings
from app.notifications.base import OutboundMessage
from app.notifications.whatsapp_cloud import WhatsAppCloudProvider, verify_webhook_signature

MESSAGE = OutboundMessage(
    to_phone_e164="+212612345671",
    template_name="convocation_tournoi",
    variables=["Youssef", "Championnat régional", "12/11/2026", "Casablanca", "08:30"],
)


@pytest.fixture(autouse=True)
def _whatsapp_credentials() -> Iterator[None]:
    """Identifiants factices : le fournisseur refuse de démarrer sans eux."""
    previous = (
        settings.WHATSAPP_PHONE_NUMBER_ID,
        settings.WHATSAPP_ACCESS_TOKEN,
        settings.WHATSAPP_APP_SECRET,
    )
    settings.WHATSAPP_PHONE_NUMBER_ID = "123456"
    settings.WHATSAPP_ACCESS_TOKEN = "jeton-de-test"
    settings.WHATSAPP_APP_SECRET = "secret-application"
    yield
    (
        settings.WHATSAPP_PHONE_NUMBER_ID,
        settings.WHATSAPP_ACCESS_TOKEN,
        settings.WHATSAPP_APP_SECRET,
    ) = previous


def _provider(handler: httpx.MockTransport) -> WhatsAppCloudProvider:
    return WhatsAppCloudProvider(client=httpx.AsyncClient(transport=handler))


def test_sans_identifiants_le_fournisseur_refuse_de_demarrer() -> None:
    settings.WHATSAPP_ACCESS_TOKEN = ""
    with pytest.raises(RuntimeError, match="WHATSAPP_PHONE_NUMBER_ID"):
        WhatsAppCloudProvider()


async def test_la_requete_respecte_le_format_attendu_par_meta() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"messages": [{"id": "wamid.ABC"}]})

    result = await _provider(httpx.MockTransport(handler)).send(MESSAGE)

    assert result.success
    assert result.provider_message_id == "wamid.ABC"
    assert captured["url"] == f"{settings.WHATSAPP_API_BASE_URL}/123456/messages"
    assert captured["auth"] == "Bearer jeton-de-test"

    body = captured["body"]
    assert isinstance(body, dict)
    assert body["messaging_product"] == "whatsapp"
    # L'API attend le numéro sans le « + ».
    assert body["to"] == "212612345671"
    assert body["template"]["name"] == "convocation_tournoi"
    assert body["template"]["language"]["code"] == "fr"
    parameters = body["template"]["components"][0]["parameters"]
    assert [p["text"] for p in parameters] == MESSAGE.variables


async def test_erreur_4xx_non_relancable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400, json={"error": {"message": "Template introuvable", "code": 132001}}
        )

    result = await _provider(httpx.MockTransport(handler)).send(MESSAGE)

    assert not result.success
    assert not result.retryable
    assert "Template introuvable" in (result.error or "")


async def test_erreur_5xx_relancable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "Service indisponible"}})

    result = await _provider(httpx.MockTransport(handler)).send(MESSAGE)
    assert not result.success
    assert result.retryable


@pytest.mark.parametrize("status_code", [408, 429])
async def test_les_erreurs_temporaires_4xx_sont_relancables(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": {"message": "trop de requêtes"}})

    result = await _provider(httpx.MockTransport(handler)).send(MESSAGE)
    assert result.retryable


async def test_panne_reseau_relancable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connexion refusée")

    result = await _provider(httpx.MockTransport(handler)).send(MESSAGE)
    assert not result.success
    assert result.retryable


async def test_reponse_sans_identifiant_de_message_est_un_echec() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"messages": []})

    result = await _provider(httpx.MockTransport(handler)).send(MESSAGE)
    assert not result.success
    assert not result.retryable


def _signature(body: bytes, secret: str = "secret-application") -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_signature_valide_acceptee() -> None:
    body = b'{"entry":[]}'
    assert verify_webhook_signature(body, _signature(body))


def test_signature_invalide_refusee() -> None:
    body = b'{"entry":[]}'
    assert not verify_webhook_signature(body, _signature(body, secret="mauvais-secret"))
    assert not verify_webhook_signature(body, "sha256=00")
    assert not verify_webhook_signature(body, None)
    assert not verify_webhook_signature(body, "pas-un-prefixe")


def test_corps_modifie_invalide_la_signature() -> None:
    signature = _signature(b'{"entry":[]}')
    assert not verify_webhook_signature(b'{"entry":[{"falsifie":true}]}', signature)


def test_sans_secret_configure_tout_webhook_est_refuse() -> None:
    body = b'{"entry":[]}'
    signature = _signature(body)
    settings.WHATSAPP_APP_SECRET = ""
    assert not verify_webhook_signature(body, signature)
