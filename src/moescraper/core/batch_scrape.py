from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, TYPE_CHECKING

from tqdm import tqdm

from moescraper.core.models import Post, Rating
from moescraper.core.downloader import download_posts, default_filename

if TYPE_CHECKING:
    from moescraper.client import MoeScraperClient


NsfwMode = Literal["safe", "all", "nsfw"]


@dataclass
class ScrapeConfig:
    source: str
    tags: list[str]
    target: int

    out_dir: Path = Path("out/images")
    meta_jsonl: Path = Path("out/metadata.jsonl")

    index_db: Path = Path("out/index.sqlite")
    state_path: Path = Path("out/scrape_state.json")

    page_start: int = 1
    limit: int = 200

    nsfw_mode: NsfwMode = "safe"
    min_width: Optional[int] = None
    min_height: Optional[int] = None

    max_workers: int = 4
    overwrite: bool = False
    resume: bool = True
    max_empty_pages: int = 10

    # File-type filter
    allowed_exts: Optional[set[str]] = None  # contoh: {"jpg", "png"}
    allow_unknown_ext: bool = False

    # Post-process downloaded files
    freeze_apng: bool = True


class IndexDB:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts(
                key TEXT PRIMARY KEY,
                source TEXT,
                post_id TEXT,
                md5 TEXT,
                file_url TEXT,
                preview_url TEXT,
                rating TEXT,
                width INTEGER,
                height INTEGER,
                tags TEXT,
                file_ext TEXT,
                local_path TEXT,
                downloaded INTEGER DEFAULT 0,
                exported INTEGER DEFAULT 0
            );
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_downloaded ON posts(downloaded);")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def key_of(p: Post) -> str:
        return p.md5 if p.md5 else f"{p.source}:{p.post_id}"

    def count_downloaded(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM posts WHERE downloaded=1;")
        return int(cur.fetchone()[0])

    def insert_posts(self, posts: list[Post]) -> None:
        rows = []
        for p in posts:
            rows.append(
                (
                    self.key_of(p),
                    p.source,
                    p.post_id,
                    p.md5,
                    p.file_url,
                    p.preview_url,
                    p.rating.value,
                    p.width,
                    p.height,
                    " ".join(p.tags or []),
                    p.file_ext,
                )
            )
        self.conn.executemany(
            """
            INSERT OR IGNORE INTO posts
            (key, source, post_id, md5, file_url, preview_url, rating, width, height, tags, file_ext)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()

    def mark_downloaded(self, posts: list[Post], out_dir: Path) -> None:
        updates = []
        for p in posts:
            dst = out_dir / default_filename(p)
            if dst.exists():
                updates.append((str(dst), self.key_of(p)))
        if updates:
            self.conn.executemany(
                "UPDATE posts SET downloaded=1, local_path=? WHERE key=?",
                updates,
            )
            self.conn.commit()

    def export_new_downloaded_to_jsonl(self, jsonl_path: Path) -> int:
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)

        cur = self.conn.execute(
            """
            SELECT key, source, post_id, file_url, preview_url, rating, width, height, md5, file_ext, tags, local_path
            FROM posts
            WHERE downloaded=1 AND exported=0
            """
        )
        rows = cur.fetchall()
        if not rows:
            return 0

        with jsonl_path.open("a", encoding="utf-8") as f:
            for (
                key,
                source,
                post_id,
                file_url,
                preview_url,
                rating,
                width,
                height,
                md5,
                file_ext,
                tags,
                local_path,
            ) in rows:
                payload = {
                    "source": source,
                    "post_id": post_id,
                    "file_url": file_url,
                    "preview_url": preview_url,
                    "rating": rating,
                    "width": width,
                    "height": height,
                    "md5": md5,
                    "file_ext": file_ext,
                    "tags": tags.split() if tags else [],
                    "local_path": local_path,
                }
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")

        self.conn.executemany("UPDATE posts SET exported=1 WHERE key=?", [(r[0],) for r in rows])
        self.conn.commit()
        return len(rows)


def _apply_nsfw_mode(posts: list[Post], mode: NsfwMode) -> list[Post]:
    if mode == "all":
        return posts
    if mode == "nsfw":
        return [p for p in posts if p.rating == Rating.NSFW]
    return [p for p in posts if p.rating == Rating.SAFE]


def _apply_min_size(posts: list[Post], min_w: Optional[int], min_h: Optional[int]) -> list[Post]:
    if min_w is None and min_h is None:
        return posts
    out: list[Post] = []
    for p in posts:
        if p.width is None or p.height is None:
            out.append(p)
            continue
        if min_w is not None and p.width < min_w:
            continue
        if min_h is not None and p.height < min_h:
            continue
        out.append(p)
    return out


def scrape_to_count(client: "MoeScraperClient", cfg: ScrapeConfig) -> None:
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    cfg.meta_jsonl.parent.mkdir(parents=True, exist_ok=True)

    db = IndexDB(cfg.index_db)
    try:
        page = cfg.page_start
        if cfg.resume and cfg.state_path.exists():
            try:
                st = json.loads(cfg.state_path.read_text(encoding="utf-8"))
                if (
                    st.get("source") == cfg.source
                    and st.get("tags") == cfg.tags
                    and st.get("nsfw_mode") == cfg.nsfw_mode
                    and st.get("allowed_exts") == (sorted(cfg.allowed_exts) if cfg.allowed_exts else None)
                    and st.get("allow_unknown_ext") == cfg.allow_unknown_ext
                ):
                    page = int(st.get("page", page))
            except Exception:
                pass

        downloaded = db.count_downloaded()
        pbar = tqdm(total=cfg.target, initial=min(downloaded, cfg.target), desc="Images", unit="img")

        empty_pages = 0
        while downloaded < cfg.target:
            search_nsfw = cfg.nsfw_mode in ("all", "nsfw")

            batch = client.search(
                source=cfg.source,
                tags=cfg.tags,
                page=page,
                limit=cfg.limit,
                nsfw=search_nsfw,
                allowed_exts=cfg.allowed_exts,
                allow_unknown_ext=cfg.allow_unknown_ext,
            )

            batch = _apply_nsfw_mode(batch, cfg.nsfw_mode)
            batch = _apply_min_size(batch, cfg.min_width, cfg.min_height)

            if not batch:
                empty_pages += 1
                pbar.set_postfix(page=page, downloaded=downloaded, empty=empty_pages)
                if empty_pages >= cfg.max_empty_pages:
                    break
                page += 1
                continue

            empty_pages = 0

            db.insert_posts(batch)

            remaining = cfg.target - downloaded
            batch = batch[:remaining]

            downloaded_paths = download_posts(
                batch,
                cfg.out_dir,
                max_workers=cfg.max_workers,
                overwrite=cfg.overwrite,
                user_agent=client.http.cfg.user_agent,
                allowed_exts=cfg.allowed_exts,
                allow_unknown_ext=cfg.allow_unknown_ext,
                freeze_apng=cfg.freeze_apng,
            )

            db.mark_downloaded(batch, cfg.out_dir)
            db.export_new_downloaded_to_jsonl(cfg.meta_jsonl)

            downloaded = db.count_downloaded()
            pbar.update(min(len(downloaded_paths), cfg.target - pbar.n))
            pbar.set_postfix(page=page, downloaded=downloaded)

            cfg.state_path.parent.mkdir(parents=True, exist_ok=True)
            cfg.state_path.write_text(
                json.dumps(
                    {
                        "source": cfg.source,
                        "tags": cfg.tags,
                        "nsfw_mode": cfg.nsfw_mode,
                        "allowed_exts": (sorted(cfg.allowed_exts) if cfg.allowed_exts else None),
                        "allow_unknown_ext": cfg.allow_unknown_ext,
                        "page": page + 1,
                        "updated_at": int(time.time()),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            page += 1

        pbar.close()
    finally:
        db.close()