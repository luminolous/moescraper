from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from .models import Post
from .rate_limit import RateLimiter
from .utils import guess_ext_from_url, domain_of

try:
    from PIL import Image

    _PIL_OK = True
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    _PIL_OK = False


def _normalize_ext(ext: str | None) -> str | None:
    if not ext:
        return None
    e = ext.lower().strip()
    if e.startswith("."):
        e = e[1:]
    if e == "jpeg":
        e = "jpg"
    return e or None


def _detect_ext(post: Post) -> str | None:
    return _normalize_ext(post.file_ext) or (
        _normalize_ext(guess_ext_from_url(post.file_url)) if post.file_url else None
    )


def _freeze_apng_inplace(path: Path) -> bool:
    """If the file is an animated PNG (APNG), rewrite it as a still PNG.

    Returns True when a conversion happened.
    """
    if not _PIL_OK:
        return False
    try:
        with Image.open(path) as im:  # type: ignore[misc]
            is_anim = bool(getattr(im, "is_animated", False))
            n_frames = int(getattr(im, "n_frames", 1))
            if not (is_anim and n_frames > 1):
                return False

            try:
                im.seek(0)
            except Exception:
                pass

            still = im.convert("RGBA") if im.mode not in ("RGB", "RGBA") else im

            tmp = path.with_suffix(path.suffix + ".still.part")
            still.save(tmp, format="PNG")
            os.replace(tmp, path)
            return True
    except Exception:
        # Jangan bikin gagal download hanya karena post-process.
        return False


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_", ".", "@") else "_" for c in name)


def default_filename(post: Post) -> str:
    ext = _detect_ext(post) or "jpg"
    md5p = (post.md5[:8] if post.md5 else "nomd5")
    return _safe_filename(f"{post.source}_{post.post_id}_{md5p}.{ext}")


def _default_referer_for(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/"


def download_posts(
    posts: list[Post],
    out_dir: str | Path,
    *,
    max_workers: int = 1,
    overwrite: bool = False,
    timeout_s: float = 60.0,
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    raise_on_error: bool = False,
    allowed_exts: set[str] | None = None,
    allow_unknown_ext: bool = False,
    freeze_apng: bool = True,
) -> list[Path]:
    """
    Download posts with:
    - browser-like User-Agent (hindari 403 WAF)
    - Referer otomatis sesuai domain file_url
    - rate-limit ringan per-domain
    - fallback: kalau 403 pada file_url, coba preview_url
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    limiter = RateLimiter(min_interval_s=0.8, jitter_s=0.2)

    client = httpx.Client(
        timeout=timeout_s,
        follow_redirects=True,
        headers={
            "User-Agent": user_agent,
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
    )

    downloaded: list[Path] = []
    errors: list[str] = []
    warned_pillow_missing = False

    def _fetch_to(url: str, dst: Path) -> None:
        limiter.wait(domain_of(url))
        headers = {"Referer": _default_referer_for(url)}
        tmp = dst.with_suffix(dst.suffix + ".part")
        try:
            with client.stream("GET", url, headers=headers) as r:
                r.raise_for_status()
                with tmp.open("wb") as f:
                    for chunk in r.iter_bytes(chunk_size=1024 * 128):
                        if chunk:
                            f.write(chunk)
            os.replace(tmp, dst)
        finally:
            if tmp.exists() and not dst.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    def _one(p: Post) -> Optional[Path]:
        if not p.file_url:
            return None

        ext = _detect_ext(p)
        if allowed_exts:
            allowed = {_normalize_ext(x) for x in allowed_exts}
            allowed.discard(None)
            if not ext:
                if not allow_unknown_ext:
                    return None
            else:
                if ext not in allowed:
                    return None

        dst = out_dir / default_filename(p)
        if dst.exists() and not overwrite:
            return dst

        try:
            _fetch_to(p.file_url, dst)

            # Post-process: freeze APNG -> PNG still (optional)
            if freeze_apng and (ext == "png" or ext is None):
                nonlocal warned_pillow_missing
                if not _PIL_OK and not warned_pillow_missing:
                    warned_pillow_missing = True
                    print(
                        "[moescraper] PIL/Pillow belum terpasang; skip freeze APNG. "
                        "Install: pip install Pillow"
                    )
                else:
                    _freeze_apng_inplace(dst)

            return dst
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 403 and p.preview_url and p.preview_url != p.file_url:
                try:
                    _fetch_to(p.preview_url, dst)
                    return dst
                except Exception as e2:
                    errors.append(f"[{p.source} #{p.post_id}] preview_url failed: {type(e2).__name__}: {e2}")
                    return None

            errors.append(f"[{p.source} #{p.post_id}] {status} for {p.file_url}")
            return None
        except Exception as e:
            errors.append(f"[{p.source} #{p.post_id}] {type(e).__name__}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_one, p) for p in posts]
        for fut in as_completed(futs):
            path = fut.result()
            if path:
                downloaded.append(path)

    client.close()

    if errors:
        msg = "Download errors (showing up to 5):\n" + "\n".join(errors[:5])
        if raise_on_error:
            raise RuntimeError(msg)
        print(msg)

    return downloaded