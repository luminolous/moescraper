from __future__ import annotations

from typing import Dict, Optional

from moescraper.adapters.base import Adapter
from moescraper.core.filters import filter_posts
from moescraper.core.models import Post
from moescraper.core.writers import write_jsonl


class MoeScraperClient:
    def __init__(self) -> None:
        self._adapters: Dict[str, Adapter] = {}

    def register(self, adapter: Adapter) -> None:
        self._adapters[adapter.source] = adapter

    def search(
        self,
        *,
        source: str,
        tags: list[str],
        page: int = 1,
        limit: int = 20,
        nsfw: bool = False,
        min_width: Optional[int] = None,
        min_height: Optional[int] = None,
    ) -> list[Post]:
        if source not in self._adapters:
            raise KeyError(
                f"Unknown source: {source}. Registered: {list(self._adapters.keys())}"
            )

        posts = self._adapters[source].search(tags=tags, page=page, limit=limit)
        posts = [p.normalized() for p in posts]
        return filter_posts(posts, nsfw=nsfw, min_width=min_width, min_height=min_height)

    def save_metadata_jsonl(self, posts: list[Post], out_jsonl: str) -> None:
        write_jsonl(posts, out_jsonl)