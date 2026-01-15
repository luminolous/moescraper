from __future__ import annotations

import re
from urllib.parse import urlparse


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower()


def sanitize_json_text(text: str) -> str:
    return _CONTROL_CHARS_RE.sub("", text)


def guess_ext_from_url(url: str) -> str | None:
    path = urlparse(url).path
    if "." not in path:
        return None
    ext = path.rsplit(".", 1)[-1].lower()
    if 1 <= len(ext) <= 5:
        return ext
    return None