from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from moescraper.core.http import HttpClient
from moescraper.core.models import Post


class BaseAdapter(ABC):
    source_name: str
    hard_limit: Optional[int] = None

    def __init__(self, http: HttpClient):
        self.http = http

    def clamp(self, *, page: int, limit: int, default_limit: int = 20) -> tuple[int, int]:
        """Normalize page/limit consistently across adapters."""
        p = max(int(page), 1)
        l = default_limit if limit is None else int(limit)
        l = max(l, 1)
        if self.hard_limit is not None:
            l = min(l, self.hard_limit)
        return p, l

    def build_query(self, tags: list[str]) -> str:
        """Default tag joiner (space-separated)."""
        return " ".join(t for t in tags if t)

    @abstractmethod
    def search(self, tags: list[str], page: int, limit: int, nsfw: bool) -> list[Post]:
        raise NotImplementedError