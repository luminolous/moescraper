from __future__ import annotations

from .models import Post, Rating
from .utils import guess_ext_from_url


def normalize_ext(ext: str | None) -> str | None:
    """Normalize extension to a stable lowercase form.

    - drops leading '.'
    - maps 'jpeg' -> 'jpg'
    """
    if not ext:
        return None
    e = ext.lower().strip()
    if e.startswith("."):
        e = e[1:]
    if e == "jpeg":
        e = "jpg"
    return e or None


def passes_file_ext(
    post: Post,
    allowed_exts: set[str] | None,
    *,
    allow_unknown_ext: bool = False,
) -> bool:
    """Return True if post is allowed by extension.

    - If allowed_exts is None/empty, accept all.
    - If extension is missing/unknown:
        - accept only when allow_unknown_ext=True
    """
    if not allowed_exts:
        return True

    allowed = {normalize_ext(x) for x in allowed_exts}
    allowed.discard(None)

    ext = normalize_ext(post.file_ext)
    if not ext and post.file_url:
        ext = normalize_ext(guess_ext_from_url(post.file_url))

    if not ext:
        return bool(allow_unknown_ext)
    return ext in allowed


def normalize_rating(value: str | None, source: str) -> Rating:
    if not value:
        return Rating.UNKNOWN

    v = value.lower().strip()

    if source == "danbooru":
        if v in ("g", "general"):
            return Rating.SAFE
        if v in ("s", "sensitive"):
            return Rating.SENSITIVE
        if v in ("q", "questionable", "e", "explicit"):
            return Rating.NSFW

    if source == "safebooru":
        return Rating.SAFE
    
    if v in ("safe", "s", "general"):
        return Rating.SAFE
    
    if v in ("questionable", "q", "explicit", "e"):
        return Rating.NSFW

    return Rating.UNKNOWN


def passes_nsfw(post: Post, nsfw: bool) -> bool:
    return True if nsfw else (post.rating != Rating.NSFW)


def passes_min_size(post: Post, *, min_width: int | None, min_height: int | None) -> bool:
    if min_width is None and min_height is None:
        return True
    if post.width is None or post.height is None:
        return True
    if min_width is not None and post.width < min_width:
        return False
    if min_height is not None and post.height < min_height:
        return False
    return True


def filter_posts(
    posts: list[Post],
    nsfw: bool,
    min_width: int | None = None,
    min_height: int | None = None,
    allowed_exts: set[str] | None = None,
    allow_unknown_ext: bool = False,
) -> list[Post]:
    out: list[Post] = []
    for p in posts:
        if not passes_nsfw(p, nsfw):
            continue
        if not passes_min_size(p, min_width=min_width, min_height=min_height):
            continue
        if not passes_file_ext(p, allowed_exts, allow_unknown_ext=allow_unknown_ext):
            continue
        out.append(p)
    return out