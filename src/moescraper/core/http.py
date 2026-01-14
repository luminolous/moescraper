from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from .rate_limit import RateLimiter
from .retry import RetryConfig, request_with_retry
from .utils import domain_of, sanitize_json_text


@dataclass
class HttpConfig:
    user_agent: str = "moescraper/0.1 (+https://github.com/yourname/moescraper)"
    timeout_s: float = 25.0
    follow_redirects: bool = True
    rate_limit_min_interval_s: float = 0.8
    rate_limit_jitter_s: float = 0.2
    retry: RetryConfig = field(default_factory=RetryConfig)


class HttpClient:
    def __init__(self, cfg: Optional[HttpConfig] = None):
        self.cfg = cfg or HttpConfig()
        self.limiter = RateLimiter(
            min_interval_s=self.cfg.rate_limit_min_interval_s,
            jitter_s=self.cfg.rate_limit_jitter_s,
        )
        self.client = httpx.Client(
            timeout=self.cfg.timeout_s,
            follow_redirects=self.cfg.follow_redirects,
            headers={"User-Agent": self.cfg.user_agent},
        )

    def close(self) -> None:
        self.client.close()

    def get_text(self, url: str, params: dict[str, Any] | None = None) -> str:
        self.limiter.wait(domain_of(url))
        resp = request_with_retry(self.client, "GET", url, self.cfg.retry, params=params)
        resp.raise_for_status()
        return resp.text

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        text = self.get_text(url, params=params)
        # some sites can return “dirty json”
        cleaned = sanitize_json_text(text)
        return httpx.Response(200, text=cleaned).json()
