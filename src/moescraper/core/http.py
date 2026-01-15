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
    def __init__(self, cfg, limiter):
        self.cfg = cfg
        self.limiter = limiter
        self.client = httpx.Client(
            headers={"User-Agent": cfg.user_agent},
            timeout=cfg.timeout_s,
            follow_redirects=True,  # penting untuk sebagian site
        )

    def get_json(self, url: str, params=None, headers=None):
        self.limiter.wait(domain_of(url))
        resp = request_with_retry(self.client, "GET", url, self.cfg.retry, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def get_text(self, url: str, params=None, headers=None):
        self.limiter.wait(domain_of(url))
        resp = request_with_retry(self.client, "GET", url, self.cfg.retry, params=params, headers=headers)
        resp.raise_for_status()
        return resp.text
