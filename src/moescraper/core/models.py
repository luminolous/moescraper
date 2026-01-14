from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


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


@dataclass
class Post:
    source: str
    post_id: str

    file_url: str
    preview_url: Optional[str] = None

    tags: list[str] = field(default_factory=list)
    rating: str = "unknown"  # "safe" | "questionable" | "explicit" | "unknown"

    width: Optional[int] = None
    height: Optional[int] = None
    md5: Optional[str] = None

    extra: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "Post":
        self.tags = normalize_tags(self.tags)
        self.rating = (self.rating or "unknown").strip().lower()
        return self

    def suggested_filename(self) -> str:
        return self.md5 or f"{self.source}_{self.post_id}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)