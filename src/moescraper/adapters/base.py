from __future__ import annotations

from typing import Protocol

from moescraper.core.models import Post


class Adapter(Protocol):
    """
    Kontrak adapter:
      - source: str
      - search(tags, page, limit) -> list[Post]

    Structural subtyping (static duck typing) via Protocol (PEP 544). :contentReference[oaicite:2]{index=2}
    """
    source: str

    def search(self, tags: list[str], page: int = 1, limit: int = 20) -> list[Post]:
        ...