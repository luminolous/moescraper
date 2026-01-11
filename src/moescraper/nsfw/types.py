from __future__ import annotations
from enum import Enum

class Rating(str, Enum):
    SAFE = "safe"
    QUESTIONABLE = "questionable"
    EXPLICIT = "explicit"
    UNKNOWN = "unknown"

class NsfwPolicy(str, Enum):
    SFW = "sfw"            # SAFE only
    SFW_PLUS = "sfw_plus"  # SAFE + QUESTIONABLE
    ALL = "all"            # everything

def rating_allowed(rating: Rating, policy: NsfwPolicy) -> bool:
    if policy == NsfwPolicy.ALL:
        return True
    if policy == NsfwPolicy.SFW_PLUS:
        return rating in (Rating.SAFE, Rating.QUESTIONABLE)
    # default SFW
    return rating == Rating.SAFE
