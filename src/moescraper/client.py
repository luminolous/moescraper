from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from moescraper.core.http import HttpClient, HttpConfig
from moescraper.core.models import Post
from moescraper.core.filters import filter_posts
from moescraper.core.downloader import download_posts
from moescraper.core.metadata import write_jsonl, write_csv

from moescraper.adapters import (
    DanbooruAdapter,
    SafebooruAdapter,
    ZerochanAdapter,
    AnimePicturesAdapter,
)


SourceName = Literal["danbooru", "safebooru", "zerochan", "anime_pictures"]


@dataclass
class MoeScraperClient:
    http_cfg: Optional[HttpConfig] = None

    def __post_init__(self) -> None:
        self.http = HttpClient(self.http_cfg)
        self.adapters = {
            "danbooru": DanbooruAdapter(self.http),
            "safebooru": SafebooruAdapter(self.http),
            "zerochan": ZerochanAdapter(self.http),
            "anime_pictures": AnimePicturesAdapter(self.http),
        }

    def close(self) -> None:
        self.http.close()

    def search(
        self,
        *,
        source: SourceName,
        tags: list[str] | str | None = None,
        page: int = 1,
        limit: int = 20,
        nsfw: bool = False,
    ) -> list[Post]:
        if isinstance(tags, str):
            tags_list = [t for t in tags.split() if t]
        else:
            tags_list = tags or []

        adapter = self.adapters[source]
        posts = adapter.search(tags_list, page=page, limit=limit, nsfw=nsfw)
        return filter_posts(posts, nsfw=nsfw)

    def download(
        self,
        posts: list[Post],
        *,
        out_dir: str = "out/images",
        max_workers: int = 6,
        overwrite: bool = False,
    ):
        return download_posts(
            posts,
            out_dir=out_dir,
            max_workers=max_workers,
            overwrite=overwrite,
        )

    def write_metadata_jsonl(self, posts: list[Post], out_path: str = "out/metadata.jsonl") -> None:
        write_jsonl(posts, out_path)

    def write_metadata_csv(self, posts: list[Post], out_path: str = "out/metadata.csv") -> None:
        write_csv(posts, out_path)