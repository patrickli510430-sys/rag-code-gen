from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from src.crawler.base import BaseCrawler, CrawledDocument

logger = logging.getLogger(__name__)


class DocCrawler(BaseCrawler):
    async def crawl(self, start_url: str) -> list[CrawledDocument]:
        documents: list[CrawledDocument] = []
        to_visit = [start_url]
        base_domain = urlparse(start_url).netloc

        while to_visit and self._can_crawl():
            url = to_visit.pop(0)
            if self._is_visited(url):
                continue

            try:
                html = await self._fetch(url)
                self._mark_visited(url)
            except Exception:
                logger.warning("Failed to fetch %s", url)
                continue

            doc = self._parse_html(url, html)
            if doc.content.strip():
                documents.append(doc)

            for link in self._extract_links(html, url):
                if urlparse(link).netloc == base_domain and not self._is_visited(link):
                    to_visit.append(link)

            await self._rate_limit()

        return documents

    def _parse_html(self, url: str, html: str) -> CrawledDocument:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title else ""
        main = soup.find("main") or soup.find("article") or soup.body
        text = main.get_text(separator="\n", strip=True) if main else ""
        text = self._clean_text(text)

        return CrawledDocument(
            url=url,
            title=title,
            content=text,
            source_type="documentation",
            crawled_at=datetime.now(timezone.utc).isoformat(),
        )

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base_url, href)
            if full_url.startswith("http") and not full_url.endswith((".png", ".jpg", ".pdf", ".zip")):
                links.append(full_url)
        return links

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    async def _rate_limit(self, seconds: float = 1.0):
        await asyncio.sleep(seconds)
