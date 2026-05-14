import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.crawler.base import CrawledDocument
from src.crawler.doc_crawler import DocCrawler
from src.crawler.code_crawler import CodeCrawler


class TestDocCrawler:
    @pytest.mark.asyncio
    async def test_crawl_with_mock(self):
        html_content = """
        <html><head><title>Test SQL Docs</title></head>
        <body>
          <main>
            <h1>SELECT Statement</h1>
            <p>The SELECT statement is used to query data from a database.</p>
            <p>Basic syntax: SELECT column FROM table WHERE condition</p>
          </main>
          <a href="/page2.html">Next Page</a>
        </body></html>
        """

        crawler = DocCrawler(max_pages=2)
        with patch.object(crawler, '_fetch', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = html_content
            docs = await crawler.crawl("https://example.com/docs")

            assert len(docs) > 0
            assert isinstance(docs[0], CrawledDocument)
            assert docs[0].source_type == "documentation"

    @pytest.mark.asyncio
    async def test_parse_html(self):
        html = """
        <html><head><title>Python Guide</title></head>
        <body>
          <main>
            <h1>Functions</h1>
            <p>Defining functions in Python.</p>
          </main>
        </body></html>
        """
        crawler = DocCrawler()
        doc = crawler._parse_html("https://example.com/python", html)
        assert doc.title == "Python Guide"
        assert "Functions" in doc.content
        assert doc.url == "https://example.com/python"

    def test_clean_text(self):
        crawler = DocCrawler()
        text = "hello   world\n\n\n\nfoo  bar"
        cleaned = crawler._clean_text(text)
        assert "hello world" in cleaned or "hello   world" not in cleaned
        assert "\n\n\n\n" not in cleaned


class TestCodeCrawler:
    @pytest.mark.asyncio
    async def test_fetch_code_file(self):
        crawler = CodeCrawler()
        code_content = "def hello():\n    return 'world'"
        with patch.object(crawler, '_fetch', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = code_content
            doc = await crawler._fetch_code_file("https://example.com/hello.py")
            assert doc is not None
            assert isinstance(doc, CrawledDocument)
            assert doc.source_type == "code/python"

    @pytest.mark.asyncio
    async def test_parse_github_url(self):
        crawler = CodeCrawler()
        urls = crawler._parse_github_url("https://github.com/user/repo/blob/main/script.py")
        assert len(urls) > 0
        assert "raw.githubusercontent.com" in urls[0]

    def test_detect_language(self):
        crawler = CodeCrawler()
        assert crawler._detect_language("test.py", "") == "python"
        assert crawler._detect_language("query.sql", "") == "sql"
