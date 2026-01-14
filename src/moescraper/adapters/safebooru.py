from __future__ import annotations

from moescraper.core.filters import normalize_rating
from moescraper.core.models import Post
from .base import BaseAdapter


class SafebooruAdapter(BaseAdapter):
    source_name = "safebooru"
    base_url = "https://safebooru.org"

    def search(self, tags: list[str], page: int, limit: int, nsfw: bool) -> list[Post]:
        # Safebooru: DAPI, param "pid" 0-based
        pid = max(page - 1, 0)
        q = " ".join(t for t in tags if t)

        # “safebooru” harusnya safe, tapi tetap biar konsisten:
        if not nsfw:
            q = (q + " " if q else "") + "rating:safe"

        params = {
            "page": "dapi",
            "s": "post",
            "q": "index",
            "json": 1,
            "tags": q,
            "pid": pid,
            "limit": max(1, min(limit, 200)),
        }

        url = f"{self.base_url}/index.php"
        data = self.http.get_json(url, params=params)

        # bentuk response kadang list, kadang dict
        if isinstance(data, dict) and "post" in data:
            items = data["post"]
        else:
            items = data

        posts: list[Post] = []
        for item in (items or []):
            file_url = item.get("file_url") or item.get("file")
            preview = item.get("preview_url") or item.get("preview_file_url")

            def _abs(u: str | None) -> str | None:
                if not u:
                    return None
                if u.startswith("//"):
                    return "https:" + u
                if u.startswith("/"):
                    return self.base_url + u
                return u

            tag_string = item.get("tags", "")
            tags_out = [t for t in tag_string.split() if t]

            p = Post(
                source=self.source_name,
                post_id=str(item.get("id")),
                file_url=_abs(file_url),
                preview_url=_abs(preview),
                tags=tags_out,
                rating=normalize_rating(item.get("rating"), source="safebooru"),
                width=item.get("width"),
                height=item.get("height"),
                md5=item.get("md5"),
                file_ext=item.get("file_ext"),
                raw=item,
            )
            posts.append(p)

        return posts