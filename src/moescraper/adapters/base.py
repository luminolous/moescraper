from __future__ import annotations

from typing import Protocol
from moescraper.core.models import Post


class Adapter(Protocol):
    """
    Kontrak adapter:
    - harus punya attribute: source: str
    - harus punya method: search(...)
    Structural typing => class tidak wajib inherit Adapter.
    (PEP 544 / Protocols)
    """
    source: str

    def search(self, tags: list[str], page: int = 1, limit: int = 20) -> list[Post]:
        ...