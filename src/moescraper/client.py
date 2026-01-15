from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from moescraper.core.http import HttpClient, HttpConfig
from moescraper.core.models import Post
from moescraper.core.filters import filter_posts
from moescraper.core.downloader import download_posts
from moescraper.core.metadata import write_jsonl, write_csv, write_json

from moescraper.adapters.base import BaseAdapter
from moescraper.adapters import DanbooruAdapter, SafebooruAdapter, ZerochanAdapter


@dataclass
class MoeScraperClient:
    http_cfg: Optional[HttpConfig] = None
    enable_default_adapters: bool = True

    def __post_init__(self) -> None:
        self.http = HttpClient(self.http_cfg)
        self.adapters: dict[str, BaseAdapter] = {}

        if self.enable_default_adapters:
            self.register_defaults()

    def close(self) -> None:
        self.http.close()

    def register_defaults(self) -> None:
        self.register_adapter(DanbooruAdapter, source_name="danbooru")
        self.register_adapter(SafebooruAdapter, source_name="safebooru")
        self.register_adapter(ZerochanAdapter, source_name="zerochan")

    def register_adapter(
        self,
        adapter: BaseAdapter | type[BaseAdapter],
        *,
        source_name: Optional[str] = None,
        override: bool = False,
    ) -> None:
        if isinstance(adapter, type):
            name = source_name or getattr(adapter, "source_name", None)
            if not name:
                raise ValueError("Adapter class must define source_name")
            inst = adapter(self.http)
        else:
            name = source_name or getattr(adapter, "source_name", None)
            if not name:
                raise ValueError("Adapter instance must define source_name")
            inst = adapter

        if (not override) and (name in self.adapters):
            raise KeyError(f"Adapter '{name}' already registered")
        self.adapters[name] = inst

    # Backward-compat alias
    def register(self, adapter: BaseAdapter | type[BaseAdapter], *, source_name: Optional[str] = None) -> None:
        self.register_adapter(adapter, source_name=source_name, override=False)

    def available_sources(self) -> list[str]:
        return sorted(self.adapters.keys())

    def scrape_images(
        self,
        *,
        source: str,
        tags: list[str] | str | None = None,
        n_images: int = 5000,
        nsfw_mode: Literal["safe", "all", "nsfw"] = "safe",
        out_dir: str = "out/images",
        meta_jsonl: str = "out/metadata.jsonl",
        index_db: str = "out/index.sqlite",
        state_path: str = "out/scrape_state.json",
        page_start: int = 1,
        limit: int = 200,
        min_width: int | None = None,
        min_height: int | None = None,
        max_workers: int = 4,
        overwrite: bool = False,
        resume: bool = True,
        max_empty_pages: int = 10,
    ) -> None:
        from moescraper.core.batch_scrape import ScrapeConfig, scrape_to_count

        if isinstance(tags, str):
            tags_list = [t for t in tags.split() if t]
        else:
            tags_list = tags or []

        cfg = ScrapeConfig(
            source=source,
            tags=tags_list,
            target=int(n_images),
            out_dir=Path(out_dir),
            meta_jsonl=Path(meta_jsonl),
            index_db=Path(index_db),
            state_path=Path(state_path),
            page_start=int(page_start),
            limit=int(limit),
            nsfw_mode=nsfw_mode,
            min_width=min_width,
            min_height=min_height,
            max_workers=int(max_workers),
            overwrite=bool(overwrite),
            resume=bool(resume),
            max_empty_pages=int(max_empty_pages),
        )

        scrape_to_count(self, cfg)

    def search(
        self,
        *,
        source: str,
        tags: list[str] | str | None = None,
        page: int = 1,
        limit: int = 20,
        nsfw: bool = False,
        min_width: int | None = None,
        min_height: int | None = None,
    ) -> list[Post]:
        if source not in self.adapters:
            raise KeyError(f"Unknown source '{source}'. Available: {', '.join(self.available_sources())}")

        if isinstance(tags, str):
            tags_list = [t for t in tags.split() if t]
        else:
            tags_list = tags or []

        adapter = self.adapters[source]
        posts = adapter.search(tags_list, page=page, limit=limit, nsfw=nsfw)
        return filter_posts(posts, nsfw=nsfw, min_width=min_width, min_height=min_height)

    def download(
        self,
        posts: list[Post],
        *,
        out_dir: str = "out/images",
        max_workers: int = 1,
        overwrite: bool = False,
    ):
        return download_posts(
            posts,
            out_dir=out_dir,
            max_workers=max_workers,
            overwrite=overwrite,
            user_agent=self.http.cfg.user_agent,
        )

    def save_metadata(self, posts: list[Post], out_path: str = "out/metadata.jsonl") -> None:
        """Format inferred from extension: .jsonl | .json | .csv"""
        if out_path.endswith(".jsonl"):
            write_jsonl(posts, out_path)
        elif out_path.endswith(".json"):
            write_json(posts, out_path)
        elif out_path.endswith(".csv"):
            write_csv(posts, out_path)
        else:
            raise ValueError("out_path must end with .jsonl | .json | .csv")

    # Backward-compat
    def write_metadata_jsonl(self, posts: list[Post], out_path: str = "out/metadata.jsonl") -> None:
        self.save_metadata(posts, out_path)

    def write_metadata_csv(self, posts: list[Post], out_path: str = "out/metadata.csv") -> None:
        self.save_metadata(posts, out_path)