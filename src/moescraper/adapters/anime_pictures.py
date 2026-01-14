from __future__ import annotations

import re
from urllib.parse import quote_plus

from moescraper.core.models import Post, Rating
from .base import BaseAdapter


POST_ID_RE = re.compile(r"/posts/(\d+)")
IMG_RE = re.compile(r"https?://(?:oimages|images)\.anime-pictures\.net/[^\s\"']+\.(?:jpg|jpeg|png|gif|webp|avif)", re.IGNORECASE)
META_KEYWORDS_RE = re.compile(r'<meta[^>]+name="keywords"[^>]+content="([^"]+)"', re.IGNORECASE)


class AnimePicturesAdapter(BaseAdapter):
    source_name = "anime_pictures"
    base_url = "https://anime-pictures.net"

    def search(self, tags: list[str], page: int, limit: int, nsfw: bool) -> list[Post]:
        """
        HTML-based (lebih tahan perubahan API):
        1) GET /posts?lang=en&page=N (&search_tag=... dicoba)
        2) regex ambil /posts/<id>
        3) buka /posts/<id>?lang=en lalu regex ambil file_url
        """
        p0 = max(page - 1, 0)

        url = f"{self.base_url}/posts"
        params = {"lang": "en", "page": p0}

        if tags:
            # param tag tidak 100% terdokumentasi → kita “best effort”
            tag_expr = " ".join(tags)
            params["search_tag"] = tag_expr  # kalau didukung
            # beberapa site pakai "tags" atau "tag" → kamu bisa tambahin kalau perlu:
            # params["tags"] = tag_expr

        html = self.http.get_text(url, params=params)
        ids = list(dict.fromkeys(POST_ID_RE.findall(html)))  # unique preserve order
        ids = ids[: max(1, limit)]

        posts: list[Post] = []
        for pid in ids:
            post_url = f"{self.base_url}/posts/{pid}"
            post_html = self.http.get_text(post_url, params={"lang": "en"})

            m_img = IMG_RE.search(post_html)
            file_url = m_img.group(0) if m_img else None

            # tags dari meta keywords (best effort)
            tags_out: list[str] = []
            m_kw = META_KEYWORDS_RE.search(post_html)
            if m_kw:
                tags_out = [t.strip() for t in m_kw.group(1).split(",") if t.strip()]

            # rating: site punya “erotic block/unblock”, tapi dari HTML publik sulit pasti → unknown
            rating = Rating.UNKNOWN

            posts.append(
                Post(
                    source=self.source_name,
                    post_id=str(pid),
                    file_url=file_url,
                    preview_url=None,
                    tags=tags_out,
                    rating=rating,
                    raw={"post_url": post_url},
                )
            )

        # nsfw=False: buang yang jelas NSFW (di sini unknown → tetap)
        if not nsfw:
            # kalau kamu mau strict: return [p for p in posts if p.rating != Rating.UNKNOWN]
            return posts
        return posts