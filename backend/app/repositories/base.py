"""Repository générique : accès CRUD typé à une table."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.db.base import Base


class BaseRepository[ModelT: Base]:
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def list_all(self) -> list[ModelT]:
        result = await self.session.scalars(select(self.model))
        return list(result)

    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def count(self, statement: Select[Any]) -> int:
        """Compte les lignes d'une requête filtrée, sans ORDER BY ni pagination."""
        subquery = statement.order_by(None).options().subquery()
        total = await self.session.scalar(select(func.count()).select_from(subquery))
        return int(total or 0)
