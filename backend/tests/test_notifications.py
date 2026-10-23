"""Envoi, relance et suivi de livraison des notifications."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, NotificationStatus, NotificationType
from app.notifications.base import NotificationProvider, OutboundMessage, SendResult
from app.notifications.console import ConsoleProvider
from app.services.errors import NotFoundError
from app.services.notifications import NotificationService


class FailingProvider(NotificationProvider):
    """Échoue systématiquement, de façon relançable ou non selon la construction."""

    name = "failing"

    def __init__(self, *, retryable: bool) -> None:
        self.retryable = retryable
        self.calls = 0

    async def send(self, message: OutboundMessage) -> SendResult:
        self.calls += 1
        return SendResult.failure("boum", retryable=self.retryable)


async def _create_notification(session: AsyncSession, **overrides: object) -> Notification:
    notification = Notification(
        recipient_phone_e164="+212612345671",
        type=NotificationType.CONVOCATION,
        template_name="convocation_tournoi",
        payload={
            "variables": ["Youssef", "Championnat régional", "12/11/2026", "Casablanca", "08:30"],
            "language_code": "fr",
        },
        **overrides,  # type: ignore[arg-type]
    )
    session.add(notification)
    await session.commit()
    return notification


async def test_envoi_reussi_passe_en_sent(session: AsyncSession) -> None:
    notification = await _create_notification(session)
    provider = ConsoleProvider()

    result = await NotificationService(session, provider).deliver(notification.id)
    await session.commit()

    assert result.status is NotificationStatus.SENT
    assert result.provider_message_id is not None
    assert result.sent_at is not None
    assert result.attempts == 1
    assert result.error is None

    assert len(provider.sent) == 1
    assert provider.sent[0].to_phone_e164 == "+212612345671"
    assert provider.sent[0].variables[0] == "Youssef"


async def test_echec_definitif_passe_en_failed(session: AsyncSession) -> None:
    notification = await _create_notification(session)

    result = await NotificationService(session, FailingProvider(retryable=False)).deliver(
        notification.id
    )
    await session.commit()

    assert result.status is NotificationStatus.FAILED
    assert result.error == "boum"
    assert result.attempts == 1


async def test_echec_relancable_reste_queued_puis_echoue_au_dernier_essai(
    session: AsyncSession,
) -> None:
    from app.core.config import settings

    notification = await _create_notification(session)
    provider = FailingProvider(retryable=True)
    service = NotificationService(session, provider)

    for attempt in range(1, settings.NOTIFICATION_MAX_ATTEMPTS):
        result = await service.deliver(notification.id)
        assert result.status is NotificationStatus.QUEUED, f"tentative {attempt}"

    # Dernière tentative : plus de relance possible.
    result = await service.deliver(notification.id)
    await session.commit()

    assert result.status is NotificationStatus.FAILED
    assert result.attempts == settings.NOTIFICATION_MAX_ATTEMPTS
    assert provider.calls == settings.NOTIFICATION_MAX_ATTEMPTS


async def test_une_notification_deja_envoyee_n_est_pas_renvoyee(
    session: AsyncSession,
) -> None:
    """Idempotence : rejouer le job ne produit pas de second message."""
    notification = await _create_notification(session, status=NotificationStatus.SENT)
    provider = ConsoleProvider()

    await NotificationService(session, provider).deliver(notification.id)

    assert provider.sent == []


async def test_notification_inconnue_leve_not_found(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await NotificationService(session, ConsoleProvider()).deliver(uuid.uuid4())


async def test_le_webhook_fait_progresser_le_statut(session: AsyncSession) -> None:
    await _create_notification(
        session, status=NotificationStatus.SENT, provider_message_id="wamid.123"
    )
    service = NotificationService(session, ConsoleProvider())

    updated = await service.apply_provider_status("wamid.123", NotificationStatus.DELIVERED)
    assert updated is not None
    assert updated.status is NotificationStatus.DELIVERED

    updated = await service.apply_provider_status("wamid.123", NotificationStatus.READ)
    assert updated is not None
    assert updated.status is NotificationStatus.READ


async def test_le_webhook_ignore_un_statut_en_retard(session: AsyncSession) -> None:
    """Les webhooks arrivent parfois dans le désordre : ne pas régresser."""
    notification = await _create_notification(
        session, status=NotificationStatus.READ, provider_message_id="wamid.456"
    )
    service = NotificationService(session, ConsoleProvider())

    updated = await service.apply_provider_status("wamid.456", NotificationStatus.SENT)
    assert updated is not None
    assert updated.status is NotificationStatus.READ
    assert notification.status is NotificationStatus.READ


async def test_webhook_pour_un_message_inconnu_est_ignore(session: AsyncSession) -> None:
    service = NotificationService(session, ConsoleProvider())
    assert await service.apply_provider_status("wamid.inconnu", NotificationStatus.READ) is None
