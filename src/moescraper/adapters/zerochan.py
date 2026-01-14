from __future__ import annotations

import re
from urllib.parse import quote_plus

from moescraper.core.models import Post, Rating
from .base import BaseAdapter


_ADULT_TAG_RE = re.compile(r"adult only|nsfw|explicit", re.IGNORECASE)


class ZerochanAdapter(BaseAdapter):
    source_name = "zerochan"
    base_url = "https://www.zerochan.net"

    def search(self, tags: list[str], page: int, limit: int, nsfw: bool) -> list[Post]:
        # Zerochan API: tambahkan ?json atau &json ke URL normal (dan pagination p=...)
        # Kalau tags kosong, ambil latest.
        p = max(page, 1)

        if tags:
            # Zerochan biasanya pakai path /<tag> ; kalau multi-tag, gabung pakai +
            query = "+".join(quote_plus(t) for t in tags if t)
            url = f"{self.base_url}/{query}"
            params = {"p": p, "json": 1}
        else:
            url = f"{self.base_url}/"
            params = {"p": p, "json": 1}

        data = self.http.get_json(url, params=params)

        # Dari beberapa implementasi, biasanya ada field list "items"
        items = None
        if isinstance(data, dict):
            items = data.get("items") or data.get("results") or data.get("images")
        if items is None and isinstance(data, list):
            items = data
        if items is None:
            items = []

        posts: list[Post] = []
        for it in items[: max(1, limit)]:
            # Field names bisa beda-beda; ini dibuat toleran
            post_id = str(it.get("id") or it.get("image_id") or it.get("post") or it.get("pid") or "")
            file_url = it.get("full") or it.get("file") or it.get("source") or it.get("url")
            preview = it.get("thumbnail") or it.get("preview") or it.get("small")

            tags_out: list[str] = []
            t = it.get("tags")
            if isinstance(t, str):
                tags_out = [x.strip() for x in t.split(",") if x.strip()]
            elif isinstance(t, list):
                tags_out = [str(x) for x in t if x]

            # nsfw heuristic: kalau ada tag “Adult Only” dsb
            rating = Rating.UNKNOWN
            joined = " ".join(tags_out)
            if _ADULT_TAG_RE.search(joined):
                rating = Rating.NSFW
            elif not tags_out:
                rating = Rating.UNKNOWN
            else:
                rating = Rating.SAFE

            if (not nsfw) and rating == Rating.NSFW:
                continue

            posts.append(
                Post(
                    source=self.source_name,
                    post_id=post_id or "unknown",
                    file_url=file_url,
                    preview_url=preview,
                    tags=tags_out,
                    rating=rating,
                    raw=it if isinstance(it, dict) else {"value": it},
                )
            )

        return posts