from __future__ import annotations

from abc import ABC, abstractmethod

from moescraper.core.http import HttpClient
from moescraper.core.models import Post


class BaseAdapter(ABC):
    source_name: str

    def __init__(self, http: HttpClient):
        self.http = http

    @abstractmethod
    def search(self, tags: list[str], page: int, limit: int, nsfw: bool) -> list[Post]:
        raise NotImplementedError
