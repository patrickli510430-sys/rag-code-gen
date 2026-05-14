from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CrawledDocument:
    url: str
    title: str = ""
    content: str = ""
    source_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    crawled_at: str = ""


class BaseCrawler(ABC):
    def __init__(self, max_pages: int | None = None, timeout: int | None = None):
        self.max_pages = max_pages or settings.crawler_max_pages
        self.timeout = timeout or settings.crawler_timeout
        self._pages_crawled = 0
        self._visited: set[str] = set()

    @abstractmethod
    async def crawl(self, start_url: str) -> list[CrawledDocument]:
        ...

    async def _fetch(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout, connect=15.0),
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def _can_crawl(self) -> bool:
        return self._pages_crawled < self.max_pages

    def _mark_visited(self, url: str):
        self._visited.add(url)
        self._pages_crawled += 1

    def _is_visited(self, url: str) -> bool:
        return url in self._visited
