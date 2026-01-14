from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

import httpx


@dataclass
class RetryConfig:
    max_tries: int = 4
    base_backoff_s: float = 0.8
    max_backoff_s: float = 8.0
    retry_statuses: Iterable[int] = (429, 500, 502, 503, 504)


def _sleep_backoff(i: int, cfg: RetryConfig) -> None:
    # exponential backoff
    delay = min(cfg.base_backoff_s * (2 ** (i - 1)), cfg.max_backoff_s)
    time.sleep(delay)


def request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    cfg: RetryConfig,
    **kwargs,
) -> httpx.Response:
    last_exc: Exception | None = None

    for i in range(1, cfg.max_tries + 1):
        try:
            resp = client.request(method, url, **kwargs)
            if resp.status_code in cfg.retry_statuses:
                if i < cfg.max_tries:
                    _sleep_backoff(i, cfg)
                    continue
            return resp
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_exc = e
            if i < cfg.max_tries:
                _sleep_backoff(i, cfg)
                continue
            raise

    if last_exc:
        raise last_exc
    raise RuntimeError("request_with_retry: unreachable")
