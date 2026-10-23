from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        """Recherche insensible à la casse : les e-mails sont stockés normalisés."""
        statement = (
            select(User)
            .where(func.lower(User.email) == email.strip().lower())
            .options(selectinload(User.referee_profile))
        )
        return await self.session.scalar(statement)

    async def get_with_profile(self, user_id: uuid.UUID) -> User | None:
        statement = (
            select(User).where(User.id == user_id).options(selectinload(User.referee_profile))
        )
        return await self.session.scalar(statement)

    async def email_exists(self, email: str) -> bool:
        statement = select(
            select(User.id).where(func.lower(User.email) == email.strip().lower()).exists()
        )
        return bool(await self.session.scalar(statement))
