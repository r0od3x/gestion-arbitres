"""Énumérations du domaine. Les valeurs sont persistées telles quelles."""

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    REFEREE = "referee"


class RefereeGrade(StrEnum):
    REGIONAL = "regional"
    NATIONAL = "national"
    CONTINENTAL = "continental"
    INTERNATIONAL = "international"


class TournamentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class AssignmentStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class NotificationChannel(StrEnum):
    WHATSAPP = "whatsapp"


class NotificationType(StrEnum):
    CONVOCATION = "convocation"
    UPDATE = "update"
    CANCELLATION = "cancellation"
    REMINDER = "reminder"


class NotificationStatus(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


#: Transitions autorisées pour le statut d'un tournoi.
TOURNAMENT_TRANSITIONS: dict[TournamentStatus, frozenset[TournamentStatus]] = {
    TournamentStatus.DRAFT: frozenset({TournamentStatus.PUBLISHED, TournamentStatus.CANCELLED}),
    TournamentStatus.PUBLISHED: frozenset({TournamentStatus.CANCELLED, TournamentStatus.COMPLETED}),
    TournamentStatus.CANCELLED: frozenset(),
    TournamentStatus.COMPLETED: frozenset(),
}

#: Statuts de notification considérés comme définitifs (pas de mise à jour arrière).
TERMINAL_NOTIFICATION_STATUSES = frozenset({NotificationStatus.READ, NotificationStatus.FAILED})

#: Ordre de progression d'une notification, pour ignorer les webhooks hors-séquence.
NOTIFICATION_STATUS_RANK: dict[NotificationStatus, int] = {
    NotificationStatus.QUEUED: 0,
    NotificationStatus.SENT: 1,
    NotificationStatus.DELIVERED: 2,
    NotificationStatus.READ: 3,
    NotificationStatus.FAILED: 4,
}
