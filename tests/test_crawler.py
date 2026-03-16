from __future__ import annotations

import asyncio
import logging

import httpx
import pytest

from services.crawler import CrawlerConfig, crawl_site


@pytest.mark.anyio
async def test_crawl_site_deduplicates_normalized_internal_links() -> None:
    pages = {
        "https://example.com": """
            <html>
              <body>
                <a href="/docs">Docs</a>
                <a href="/docs/">Docs duplicate</a>
                <a href="https://example.com/docs?utm_source=newsletter">Docs tracking</a>
              </body>
            </html>
        """,
        "https://example.com/docs": """
            <html>
              <body>
                <a href="/guide">Guide</a>
              </body>
            </html>
        """,
        "https://example.com/guide": "<html><body><p>Guide</p></body></html>",
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        request_url = str(request.url).rstrip("/") or str(request.url)
        html = pages.get(request_url)
        if html is None:
            return httpx.Response(status_code=404, request=request)

        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            text=html,
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        crawled_pages = await crawl_site(
            "https://example.com/",
            config=CrawlerConfig(max_depth=2, max_pages=10),
            client=client,
        )

    assert [page[0] for page in crawled_pages] == [
        "https://example.com/",
        "https://example.com/docs",
        "https://example.com/guide",
    ]
    assert [page[2] for page in crawled_pages] == [0, 1, 2]


@pytest.mark.anyio
async def test_crawl_site_filters_external_and_non_html_links() -> None:
    pages = {
        "https://example.com": """
            <html>
              <body>
                <a href="/docs">Docs</a>
                <a href="https://blog.example.com/post">External subdomain</a>
                <a href="https://example.com/files/guide.pdf">PDF</a>
              </body>
            </html>
        """,
        "https://example.com/docs": "<html><body><p>Docs</p></body></html>",
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        request_url = str(request.url).rstrip("/") or str(request.url)
        html = pages.get(request_url)
        if html is None:
            return httpx.Response(status_code=404, request=request)

        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/html"},
            text=html,
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        crawled_pages = await crawl_site(
            "https://example.com",
            config=CrawlerConfig(max_depth=1, max_pages=10),
            client=client,
        )

    assert [page[0] for page in crawled_pages] == [
        "https://example.com/",
        "https://example.com/docs",
    ]


@pytest.mark.anyio
async def test_crawl_site_respects_max_pages_limit() -> None:
    pages = {
        "https://example.com": """
            <html>
              <body>
                <a href="/docs">Docs</a>
                <a href="/guide">Guide</a>
              </body>
            </html>
        """,
        "https://example.com/docs": "<html><body><p>Docs</p></body></html>",
        "https://example.com/guide": "<html><body><p>Guide</p></body></html>",
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        request_url = str(request.url).rstrip("/") or str(request.url)
        html = pages.get(request_url)
        if html is None:
            return httpx.Response(status_code=404, request=request)

        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/html"},
            text=html,
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        crawled_pages = await crawl_site(
            "https://example.com",
            config=CrawlerConfig(max_depth=2, max_pages=2),
            client=client,
        )

    assert len(crawled_pages) == 2
    assert [page[0] for page in crawled_pages] == [
        "https://example.com/",
        "https://example.com/docs",
    ]


@pytest.mark.anyio
async def test_crawl_site_fetches_same_depth_pages_concurrently() -> None:
    pages = {
        "https://example.com": """
            <html>
              <body>
                <a href="/docs">Docs</a>
                <a href="/guide">Guide</a>
              </body>
            </html>
        """,
        "https://example.com/docs": "<html><body><p>Docs</p></body></html>",
        "https://example.com/guide": "<html><body><p>Guide</p></body></html>",
    }
    active_requests = 0
    max_active_requests = 0
    lock = asyncio.Lock()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active_requests, max_active_requests

        async with lock:
            active_requests += 1
            max_active_requests = max(max_active_requests, active_requests)

        try:
            if str(request.url).rstrip("/") != "https://example.com":
                await asyncio.sleep(0.01)

            request_url = str(request.url).rstrip("/") or str(request.url)
            html = pages.get(request_url)
            if html is None:
                return httpx.Response(status_code=404, request=request)

            return httpx.Response(
                status_code=200,
                headers={"content-type": "text/html"},
                text=html,
                request=request,
            )
        finally:
            async with lock:
                active_requests -= 1

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        crawled_pages = await crawl_site(
            "https://example.com",
            config=CrawlerConfig(max_depth=1, max_pages=10, max_concurrent_requests=2),
            client=client,
        )

    assert [page[0] for page in crawled_pages] == [
        "https://example.com/",
        "https://example.com/docs",
        "https://example.com/guide",
    ]
    assert [page[2] for page in crawled_pages] == [0, 1, 1]
    assert max_active_requests >= 2


@pytest.mark.anyio
async def test_crawl_site_limits_same_depth_concurrency() -> None:
    pages = {
        "https://example.com": """
            <html>
              <body>
                <a href="/docs">Docs</a>
                <a href="/guide">Guide</a>
                <a href="/blog">Blog</a>
              </body>
            </html>
        """,
        "https://example.com/docs": "<html><body><p>Docs</p></body></html>",
        "https://example.com/guide": "<html><body><p>Guide</p></body></html>",
        "https://example.com/blog": "<html><body><p>Blog</p></body></html>",
    }
    active_requests = 0
    max_active_requests = 0
    lock = asyncio.Lock()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active_requests, max_active_requests

        async with lock:
            active_requests += 1
            max_active_requests = max(max_active_requests, active_requests)

        try:
            if str(request.url).rstrip("/") != "https://example.com":
                await asyncio.sleep(0.01)

            request_url = str(request.url).rstrip("/") or str(request.url)
            html = pages.get(request_url)
            if html is None:
                return httpx.Response(status_code=404, request=request)

            return httpx.Response(
                status_code=200,
                headers={"content-type": "text/html"},
                text=html,
                request=request,
            )
        finally:
            async with lock:
                active_requests -= 1

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        await crawl_site(
            "https://example.com",
            config=CrawlerConfig(max_depth=1, max_pages=10, max_concurrent_requests=2),
            client=client,
        )

    assert max_active_requests == 2


@pytest.mark.anyio
async def test_crawl_site_logs_lifecycle_and_fetch_timing(caplog: pytest.LogCaptureFixture) -> None:
    pages = {
        "https://example.com": "<html><body><p>Home</p></body></html>",
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        request_url = str(request.url).rstrip("/") or str(request.url)
        html = pages.get(request_url)
        if html is None:
            return httpx.Response(status_code=404, request=request)

        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/html"},
            text=html,
            request=request,
        )

    transport = httpx.MockTransport(handler)
    caplog.set_level(logging.DEBUG)
    async with httpx.AsyncClient(transport=transport) as client:
        await crawl_site(
            "https://example.com",
            config=CrawlerConfig(max_depth=0, max_pages=1),
            client=client,
        )

    assert "Starting crawl for https://example.com/" in caplog.text
    assert "Fetched https://example.com/ in " in caplog.text
    assert "Completed crawl for https://example.com/ in " in caplog.text
