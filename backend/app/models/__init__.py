"""Modèles SQLAlchemy. Tout import ici alimente Base.metadata pour Alembic."""

from app.db.base import Base
from app.models.assignment import TournamentAssignment
from app.models.enums import (
    AssignmentStatus,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    RefereeGrade,
    TournamentStatus,
    UserRole,
)
from app.models.notification import Notification
from app.models.referee import RefereeProfile
from app.models.tournament import Tournament
from app.models.user import User

__all__ = [
    "AssignmentStatus",
    "Base",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "NotificationType",
    "RefereeGrade",
    "RefereeProfile",
    "Tournament",
    "TournamentAssignment",
    "TournamentStatus",
    "User",
    "UserRole",
]
