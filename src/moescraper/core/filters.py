from __future__ import annotations

from typing import Optional

from moescraper.core.models import Post
from moescraper.nsfw.types import rating_allowed


def filter_posts(
    posts: list[Post],
    *,
    nsfw: bool = False,
    min_width: Optional[int] = None,
    min_height: Optional[int] = None,
) -> list[Post]:
    out: list[Post] = []
    for p in posts:
        if not rating_allowed(p.rating, nsfw=nsfw):
            continue

        if min_width is not None and (p.width is None or p.width < min_width):
            continue
        if min_height is not None and (p.height is None or p.height < min_height):
            continue

        out.append(p)
    return out
