from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Optional


class Rating(str, Enum):
    SAFE = "safe"              # aman
    SENSITIVE = "sensitive"    # masih “safe-ish”
    NSFW = "nsfw"              # questionable/explicit
    UNKNOWN = "unknown"        # tidak jelas


@dataclass(frozen=True)
class Post:
    source: str
    post_id: str

    file_url: Optional[str]
    preview_url: Optional[str]

    tags: list[str]
    rating: Rating

    width: Optional[int] = None
    height: Optional[int] = None
    md5: Optional[str] = None
    file_ext: Optional[str] = None

    # raw payload (berguna buat debug)
    raw: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["rating"] = self.rating.value
        return d