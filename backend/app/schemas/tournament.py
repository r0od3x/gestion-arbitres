"""Schémas des tournois et des désignations."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.assignment import TournamentAssignment
from app.models.enums import AssignmentStatus, NotificationStatus, TournamentStatus
from app.models.tournament import Tournament


class TournamentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    venue: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    convocation_time: time | None = None
    referees_needed: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_dates(self) -> TournamentCreate:
        # Doublon volontaire de la contrainte en base : le message d'erreur
        # arrive au formulaire au lieu d'une violation d'intégrité brute.
        if self.end_date < self.start_date:
            raise ValueError("La date de fin ne peut pas précéder la date de début.")
        return self


class TournamentUpdate(BaseModel):
    """Modification d'un tournoi. Le statut change par ses propres routes."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    venue: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    convocation_time: time | None = None
    referees_needed: int | None = Field(default=None, gt=0)


class TournamentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    venue: str | None
    city: str
    start_date: date
    end_date: date
    convocation_time: time | None
    referees_needed: int | None
    status: TournamentStatus
    created_at: datetime


class TournamentWithCounts(TournamentRead):
    """Vue liste : évite d'aller chercher les désignations une par une."""

    assigned_count: int = 0
    confirmed_count: int = 0

    @classmethod
    def from_row(
        cls, tournament: Tournament, assigned: int, confirmed: int
    ) -> TournamentWithCounts:
        return cls(
            **TournamentRead.model_validate(tournament).model_dump(),
            assigned_count=assigned,
            confirmed_count=confirmed,
        )


# ----------------------------------------------------------------------
# Désignations
# ----------------------------------------------------------------------


class AssignmentRefereeRead(BaseModel):
    """L'arbitre, vu depuis une désignation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    phone_e164: str | None
    whatsapp_opt_in: bool
    city: str | None


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tournament_id: uuid.UUID
    referee_id: uuid.UUID
    role_in_tournament: str | None
    status: AssignmentStatus
    responded_at: datetime | None
    created_at: datetime


class AssignmentWithReferee(AssignmentRead):
    """Vue administrateur : la désignation, l'arbitre et l'état de sa notification."""

    referee: AssignmentRefereeRead
    #: Statut de la dernière notification envoyée, si elle existe.
    notification_status: NotificationStatus | None = None
    notification_error: str | None = None
    #: Faux si l'arbitre n'a pas consenti ou n'a pas de numéro valide.
    is_notifiable: bool = False

    @classmethod
    def from_assignment(cls, assignment: TournamentAssignment) -> AssignmentWithReferee:
        # La dernière notification fait foi pour l'affichage.
        latest = max(
            assignment.notifications,
            key=lambda notification: notification.created_at,
            default=None,
        )
        return cls(
            id=assignment.id,
            tournament_id=assignment.tournament_id,
            referee_id=assignment.referee_id,
            role_in_tournament=assignment.role_in_tournament,
            status=assignment.status,
            responded_at=assignment.responded_at,
            created_at=assignment.created_at,
            referee=AssignmentRefereeRead.model_validate(assignment.referee),
            notification_status=latest.status if latest else None,
            notification_error=latest.error if latest else None,
            is_notifiable=assignment.referee.is_notifiable,
        )


class AssignmentWithTournament(AssignmentRead):
    """Vue arbitre : « mes convocations »."""

    tournament: TournamentRead

    @classmethod
    def from_assignment(cls, assignment: TournamentAssignment) -> AssignmentWithTournament:
        return cls(
            id=assignment.id,
            tournament_id=assignment.tournament_id,
            referee_id=assignment.referee_id,
            role_in_tournament=assignment.role_in_tournament,
            status=assignment.status,
            responded_at=assignment.responded_at,
            created_at=assignment.created_at,
            tournament=TournamentRead.model_validate(assignment.tournament),
        )


class AssignmentsReplace(BaseModel):
    """Liste cible des arbitres désignés : mise à jour différentielle."""

    model_config = ConfigDict(extra="forbid")

    referee_ids: list[uuid.UUID] = Field(
        description="Liste complète des arbitres qui doivent être convoqués."
    )

    @model_validator(mode="after")
    def _check_unique(self) -> AssignmentsReplace:
        if len(set(self.referee_ids)) != len(self.referee_ids):
            raise ValueError("La liste contient des arbitres en double.")
        return self


class AssignmentsDiff(BaseModel):
    """Ce que la mise à jour différentielle a changé."""

    added: int
    cancelled: int
    unchanged: int
