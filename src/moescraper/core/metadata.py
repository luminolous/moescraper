from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Post


def write_jsonl(posts: list[Post], out_path: str | Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for p in posts:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")


def write_csv(posts: list[Post], out_path: str | Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "source", "post_id", "file_url", "preview_url", "tags", "rating",
        "width", "height", "md5", "file_ext"
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for p in posts:
            d = p.to_dict()
            d["tags"] = " ".join(p.tags)
            w.writerow({k: d.get(k) for k in fieldnames})
