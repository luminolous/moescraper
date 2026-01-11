from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from moescraper.nsfw.types import Rating


def normalize_tags(tags: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for t in tags:
        tt = (t or "").strip().lower()
        if not tt:
            continue
        if tt not in seen:
            seen.add(tt)
            out.append(tt)
    return out

class Post(BaseModel):
    source: str
    post_id: str

    file_url: str
    preview_url: Optional[str] = None

    tags: list[str] = Field(default_factory=list)
    rating: Rating = Rating.UNKNOWN

    width: Optional[int] = None
    height: Optional[int] = None
    md5: Optional[str] = None

    extra: dict[str, Any] = Field(default_factory=dict)

    def normalized(self) -> "Post":
        self.tags = normalize_tags(self.tags)
        return self

    def suggested_filename(self) -> str:
        # md5 for the best dedup
        base = self.md5 or f"{self.source}_{self.post_id}"
        return base