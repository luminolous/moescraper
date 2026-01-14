from __future__ import annotations

from .models import Post, Rating


def normalize_rating(value: str | None, source: str) -> Rating:
    if not value:
        return Rating.UNKNOWN

    v = value.lower().strip()

    # Danbooru rating: g/s/q/e (general/sensitive/questionable/explicit)
    if source == "danbooru":
        if v in ("g", "general"):
            return Rating.SAFE
        if v in ("s", "sensitive"):
            return Rating.SENSITIVE
        if v in ("q", "questionable", "e", "explicit"):
            return Rating.NSFW

    # Booru/Moebooru rating: safe/questionable/explicit (kadang s/q/e)
    if v in ("safe", "s"):
        return Rating.SAFE
    if v in ("questionable", "q"):
        return Rating.NSFW
    if v in ("explicit", "e"):
        return Rating.NSFW

    return Rating.UNKNOWN


def passes_nsfw(post: Post, nsfw: bool) -> bool:
    """
    nsfw=False: buang yang jelas NSFW.
    nsfw=True : ambil semua.
    """
    if nsfw:
        return True
    return post.rating != Rating.NSFW


def filter_posts(posts: list[Post], nsfw: bool) -> list[Post]:
    return [p for p in posts if passes_nsfw(p, nsfw)]
