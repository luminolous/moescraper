from __future__ import annotations

SAFE = "safe"
QUESTIONABLE = "questionable"
EXPLICIT = "explicit"
UNKNOWN = "unknown"


def rating_allowed(rating: str, nsfw: bool) -> bool:
    r = (rating or UNKNOWN).strip().lower()
    if nsfw:
        return True
    return r == SAFE