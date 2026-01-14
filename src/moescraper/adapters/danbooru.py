from __future__ import annotations

from moescraper.core.filters import normalize_rating
from moescraper.core.models import Post
from .base import BaseAdapter


class DanbooruAdapter(BaseAdapter):
    source_name = "danbooru"
    base_url = "https://danbooru.donmai.us"

    def search(self, tags: list[str], page: int, limit: int, nsfw: bool) -> list[Post]:
        # Danbooru pakai "space-separated tags"
        q = " ".join(t for t in tags if t)

        # nsfw False: exclude q/e
        if not nsfw:
            q = (q + " " if q else "") + "-rating:q -rating:e"

        params = {
            "tags": q,
            "page": max(page, 1),
            "limit": max(1, min(limit, 200)),
        }
        url = f"{self.base_url}/posts.json"
        data = self.http.get_json(url, params=params)

        posts: list[Post] = []
        for item in data:
            file_url = item.get("file_url")
            if file_url and file_url.startswith("/"):
                file_url = self.base_url + file_url

            preview = item.get("preview_file_url") or item.get("large_file_url")
            if preview and preview.startswith("/"):
                preview = self.base_url + preview

            tag_string = item.get("tag_string", "")  # space-separated
            tags_out = [t for t in tag_string.split() if t]

            p = Post(
                source=self.source_name,
                post_id=str(item.get("id")),
                file_url=file_url,
                preview_url=preview,
                tags=tags_out,
                rating=normalize_rating(item.get("rating"), source="danbooru"),
                width=item.get("image_width"),
                height=item.get("image_height"),
                md5=item.get("md5"),
                file_ext=item.get("file_ext"),
                raw=item,
            )
            posts.append(p)

        return posts