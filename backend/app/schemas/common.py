"""Schémas transverses : pagination, erreurs, messages."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

PageNumber = Annotated[int, Field(ge=1, description="Numéro de page, commence à 1")]
PageSize = Annotated[int, Field(ge=1, le=100, description="Éléments par page")]


class Page[T](BaseModel):
    items: list[T]
    total: int = Field(description="Nombre total d'éléments correspondant au filtre")
    page: int
    size: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.size))


class Message(BaseModel):
    detail: str


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
