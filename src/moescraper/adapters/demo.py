from __future__ import annotations

from moescraper.core.models import Post
from moescraper.nsfw.types import SAFE


class DemoAdapter:
    source = "demo"

    def search(self, tags: list[str], page: int = 1, limit: int = 20) -> list[Post]:
        posts: list[Post] = []
        for i in range(limit):
            posts.append(
                Post(
                    source=self.source,
                    post_id=str((page - 1) * limit + i + 1),
                    file_url=f"https://example.com/file/{i}.jpg",
                    preview_url=f"https://example.com/preview/{i}.jpg",
                    tags=tags + ["demo_tag"],
                    rating=SAFE,
                    width=1024,
                    height=768,
                    md5=None,
                    extra={"note": "demo"},
                ).normalized()
            )
        return posts