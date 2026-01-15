# moescraper/adapters/anime_pictures.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import httpx

from moescraper.core.models import Post

API_URL_CANDIDATES = [
    "https://api.anime-pictures.net/api/v3/posts",   # sering jadi host baru
    "https://anime-pictures.net/api/v3/posts",       # fallback
]

def _as_list_tags(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str):
        # kadang "tag1 tag2" atau "tag1,tag2"
        return [t for t in v.replace(",", " ").split() if t]
    return [str(v)]

def _pick_posts_payload(data: Any) -> List[Dict[str, Any]]:
    # kemungkinan bentuk payload:
    # 1) {"posts": [...]}
    # 2) {"data": [...]}
    # 3) [...] langsung list
    if isinstance(data, dict):
        for k in ("posts", "data", "result", "items"):
            if k in data and isinstance(data[k], list):
                return data[k]
        # kadang nested
        if "response" in data and isinstance(data["response"], dict):
            return _pick_posts_payload(data["response"])
        return []
    if isinstance(data, list):
        return data
    return []

def _normalize_file_host(url: Optional[str]) -> Optional[str]:
    if not url:
        return url
    # laporan perubahan host images -> oimages :contentReference[oaicite:2]{index=2}
    return url.replace("images.anime-pictures.net", "oimages.anime-pictures.net")

@dataclass
class AnimePicturesAdapter:
    http: Any  # HttpClient kamu

    def search(self, tags: List[str], page: int = 0, limit: int = 20, nsfw: bool = False) -> List[Post]:
        tag_expr = " ".join(tags).strip()

        # beberapa kandidat nama param yang sering dipakai
        params_variants = [
            {"page": page, "limit": limit, "search_tag": tag_expr, "lang": "en"},
            {"page": page, "limit": limit, "tags": tag_expr, "lang": "en"},
            {"page": page, "limit": limit, "tag": tag_expr, "lang": "en"},
        ]

        last_err: Optional[Exception] = None

        for api_url in API_URL_CANDIDATES:
            for params in params_variants:
                try:
                    data = self.http.get_json(
                        api_url,
                        params=params,
                        # header yang “wajar” untuk endpoint JSON
                        headers={
                            "Accept": "application/json,text/plain,*/*",
                            "Referer": "https://anime-pictures.net/",
                        },
                    )
                    raw_posts = _pick_posts_payload(data)
                    if not raw_posts:
                        continue

                    out: List[Post] = []
                    for it in raw_posts[:limit]:
                        post_id = str(it.get("id") or it.get("post_id") or "")
                        file_url = _normalize_file_host(
                            it.get("file_url") or it.get("image") or it.get("url")
                        )
                        preview_url = _normalize_file_host(
                            it.get("preview_url") or it.get("sample_url") or it.get("thumb") or it.get("thumbnail")
                        )

                        width = it.get("width") or it.get("w")
                        height = it.get("height") or it.get("h")

                        # rating di Anime-Pictures kadang tidak sejelas booru lain → set "unknown"
                        rating = str(it.get("rating") or it.get("safe") or "unknown").lower()

                        tags_norm = _as_list_tags(it.get("tags"))

                        out.append(
                            Post(
                                source="anime_pictures",
                                post_id=post_id,
                                file_url=file_url,
                                preview_url=preview_url,
                                tags=tags_norm,
                                rating=rating,
                                width=int(width) if width else None,
                                height=int(height) if height else None,
                                md5=str(it.get("md5") or "") or None,
                            )
                        )

                    return out

                except httpx.HTTPStatusError as e:
                    # 403/404: coba varian endpoint/param lain
                    if e.response is not None and e.response.status_code in (403, 404):
                        last_err = e
                        continue
                    raise
                except Exception as e:
                    last_err = e
                    continue

        raise RuntimeError(
            "Anime-Pictures: API berubah atau akses diblok (403). "
            "Coba jalankan dari jaringan non-datacenter, atau pakai API endpoint terbaru."
        ) from last_err