from __future__ import annotations

import random
import time
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """
    Rate limit sederhana per-domain:
    - minimal interval antar request (seconds)
    - jitter kecil biar nggak “pola bot”
    """
    min_interval_s: float = 0.8
    jitter_s: float = 0.2
    _last_time: dict[str, float] = field(default_factory=dict)

    def wait(self, domain: str) -> None:
        now = time.time()
        last = self._last_time.get(domain, 0.0)
        elapsed = now - last

        target = self.min_interval_s + random.random() * self.jitter_s
        if elapsed < target:
            time.sleep(target - elapsed)

        self._last_time[domain] = time.time()