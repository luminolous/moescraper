from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import httpx

from .models import Post
from .utils import guess_ext_from_url


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_", ".", "@") else "_" for c in name)


def default_filename(post: Post) -> str:
    ext = post.file_ext or (guess_ext_from_url(post.file_url) if post.file_url else None) or "jpg"
    md5p = (post.md5[:8] if post.md5 else "nomd5")
    return _safe_filename(f"{post.source}_{post.post_id}_{md5p}.{ext}")


def download_posts(
    posts: list[Post],
    out_dir: str | Path,
    *,
    max_workers: int = 6,
    overwrite: bool = False,
    timeout_s: float = 60.0,
) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = httpx.Client(timeout=timeout_s, follow_redirects=True)
    downloaded: list[Path] = []

    def _one(p: Post) -> Optional[Path]:
        if not p.file_url:
            return None

        dst = out_dir / default_filename(p)
        if dst.exists() and not overwrite:
            return dst

        tmp = dst.with_suffix(dst.suffix + ".part")
        try:
            with client.stream("GET", p.file_url) as r:
                r.raise_for_status()
                with tmp.open("wb") as f:
                    for chunk in r.iter_bytes(chunk_size=1024 * 128):
                        if chunk:
                            f.write(chunk)
            os.replace(tmp, dst)
            return dst
        finally:
            if tmp.exists() and not dst.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_one, p) for p in posts]
        for fut in as_completed(futs):
            path = fut.result()
            if path:
                downloaded.append(path)

    client.close()
    return downloaded
