from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from moescraper.core.models import Post


def write_jsonl(posts: Iterable[Post], path: str | Path) -> Path:
    """
    JSONL = 1 JSON object per line (newline-delimited JSON).
    Cocok untuk dataset/streaming. :contentReference[oaicite:2]{index=2}
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for p in posts:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
    return path