from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import joinedload

from app.models.enums import RefereeGrade
from app.models.referee import RefereeProfile
from app.models.user import User
from app.repositories.base import BaseRepository


class RefereeRepository(BaseRepository[RefereeProfile]):
    model = RefereeProfile

    async def get_by_user_id(self, user_id: uuid.UUID) -> RefereeProfile | None:
        statement = select(RefereeProfile).where(RefereeProfile.user_id == user_id)
        return await self.session.scalar(statement)

    async def get_with_user(self, referee_id: uuid.UUID) -> RefereeProfile | None:
        statement = (
            select(RefereeProfile)
            .where(RefereeProfile.id == referee_id)
            .options(joinedload(RefereeProfile.user))
        )
        return await self.session.scalar(statement)

    async def get_by_phone(self, phone_e164: str) -> RefereeProfile | None:
        statement = select(RefereeProfile).where(RefereeProfile.phone_e164 == phone_e164)
        return await self.session.scalar(statement)

    async def get_by_license(self, license_number: str) -> RefereeProfile | None:
        statement = select(RefereeProfile).where(
            func.lower(RefereeProfile.license_number) == license_number.strip().lower()
        )
        return await self.session.scalar(statement)

    async def get_many(self, referee_ids: Sequence[uuid.UUID]) -> list[RefereeProfile]:
        if not referee_ids:
            return []
        statement = (
            select(RefereeProfile)
            .where(RefereeProfile.id.in_(referee_ids))
            .options(joinedload(RefereeProfile.user))
        )
        return list(await self.session.scalars(statement))

    def search_statement(
        self,
        *,
        grade: RefereeGrade | None = None,
        city: str | None = None,
        active: bool | None = None,
        query: str | None = None,
    ) -> Select[RefereeProfile]:
        """Construit la requête filtrée, réutilisée pour le comptage et la page."""
        statement = (
            select(RefereeProfile)
            .join(RefereeProfile.user)
            .options(joinedload(RefereeProfile.user))
        )
        if grade is not None:
            statement = statement.where(RefereeProfile.grade == grade)
        if city:
            statement = statement.where(func.lower(RefereeProfile.city) == city.strip().lower())
        if active is not None:
            statement = statement.where(User.is_active.is_(active))
        if query:
            pattern = f"%{query.strip().lower()}%"
            statement = statement.where(
                or_(
                    func.lower(RefereeProfile.first_name).like(pattern),
                    func.lower(RefereeProfile.last_name).like(pattern),
                    func.lower(User.email).like(pattern),
                    RefereeProfile.phone_e164.like(pattern),
                    func.lower(RefereeProfile.license_number).like(pattern),
                )
            )
        return statement

    async def search_page(
        self,
        statement: Select[RefereeProfile],
        *,
        page: int,
        size: int,
    ) -> tuple[list[RefereeProfile], int]:
        total = await self.count(statement)
        paged = (
            statement.order_by(RefereeProfile.last_name, RefereeProfile.first_name)
            .offset((page - 1) * size)
            .limit(size)
        )
        rows = list((await self.session.scalars(paged)).unique())
        return rows, total
