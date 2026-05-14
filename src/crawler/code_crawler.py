from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from src.crawler.base import BaseCrawler, CrawledDocument

logger = logging.getLogger(__name__)

CODE_EXTENSIONS = {".py", ".sql", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c", ".h"}


class CodeCrawler(BaseCrawler):
    def __init__(self, github_token: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.github_token = github_token

    async def crawl(self, start_url: str) -> list[CrawledDocument]:
        documents: list[CrawledDocument] = []

        if "github.com" in start_url:
            raw_urls = self._parse_github_url(start_url)
            for raw_url in raw_urls:
                if not self._can_crawl():
                    break
                doc = await self._fetch_code_file(raw_url)
                if doc:
                    documents.append(doc)
        elif start_url.endswith(".py") or start_url.endswith(".sql"):
            doc = await self._fetch_code_file(start_url)
            if doc:
                documents.append(doc)
        else:
            doc = await self._fetch_code_file(start_url)
            if doc:
                documents.append(doc)

        return documents

    async def _fetch_code_file(self, url: str) -> CrawledDocument | None:
        if self._is_visited(url):
            return None
        try:
            content = await self._fetch(url)
            self._mark_visited(url)
        except Exception:
            logger.warning("Failed to fetch code file %s", url)
            return None

        lang = self._detect_language(url, content)
        return CrawledDocument(
            url=url,
            title=self._extract_filename(url),
            content=content,
            source_type=f"code/{lang}",
            metadata={"language": lang},
            crawled_at=datetime.now(timezone.utc).isoformat(),
        )

    def _parse_github_url(self, url: str) -> list[str]:
        match = re.match(r"https://github\.com/([^/]+)/([^/]+)", url)
        if not match:
            return [url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")]
        owner, repo = match.groups()
        return [url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")]

    @staticmethod
    def _detect_language(url: str, _content: str) -> str:
        ext_map = {
            ".py": "python", ".sql": "sql", ".js": "javascript",
            ".ts": "typescript", ".java": "java", ".go": "go",
            ".rs": "rust", ".cpp": "cpp", ".c": "c", ".h": "c",
        }
        for ext, lang in ext_map.items():
            if url.endswith(ext):
                return lang
        return "unknown"

    @staticmethod
    def _extract_filename(url: str) -> str:
        return url.rstrip("/").rsplit("/", 1)[-1]
