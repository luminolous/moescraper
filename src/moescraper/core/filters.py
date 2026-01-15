from __future__ import annotations

from .models import Post, Rating


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

    if v in ("safe", "s"):
        return Rating.SAFE
    if v in ("questionable", "q", "explicit", "e"):
        return Rating.NSFW

    return Rating.UNKNOWN


def passes_nsfw(post: Post, nsfw: bool) -> bool:
    return True if nsfw else (post.rating != Rating.NSFW)


def passes_min_size(post: Post, *, min_width: int | None, min_height: int | None) -> bool:
    if min_width is None and min_height is None:
        return True
    # kalau dimensinya unknown, jangan dibuang (biar user masih bisa pakai)
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
) -> list[Post]:
    out: list[Post] = []
    for p in posts:
        if not passes_nsfw(p, nsfw):
            continue
        if not passes_min_size(p, min_width=min_width, min_height=min_height):
            continue
        out.append(p)
    return out