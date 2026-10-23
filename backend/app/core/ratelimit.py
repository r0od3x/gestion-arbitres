"""Limitation de débit simple, en mémoire.

Suffisant pour un process unique (dev, petite prod). Avec plusieurs workers,
remplacer le stockage par Redis — l'interface ne change pas.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from app.services.errors import DomainError


class RateLimitError(DomainError):
    status_code = 429
    code = "rate_limited"


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        """Enregistre un appel ; lève RateLimitError si le quota est dépassé."""
        now = time.monotonic()
        hits = self._hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] < cutoff:
            hits.popleft()

        if len(hits) >= self.max_calls:
            retry_after = int(hits[0] + self.window_seconds - now) + 1
            raise RateLimitError(f"Trop de tentatives. Réessayez dans {retry_after} seconde(s).")
        hits.append(now)

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._hits.clear()
        else:
            self._hits.pop(key, None)


#: 10 tentatives de connexion par IP toutes les 5 minutes.
login_limiter = SlidingWindowLimiter(max_calls=10, window_seconds=300)
