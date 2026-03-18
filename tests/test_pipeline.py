from __future__ import annotations

import logging

import httpx
import pytest

from services.crawler import CrawlerConfig
from services.pipeline import GenerationPipeline, InterstitialPageError


@pytest.mark.anyio
async def test_generation_pipeline_runs_end_to_end_with_mocked_http_site() -> None:
    pages = {
        "https://example.com": """
            <html>
              <head>
                <title>Example Platform</title>
                <meta name="description" content="Developer tools and docs for Example Platform.">
              </head>
              <body>
                <a href="/docs/start">Getting Started</a>
                <a href="/account/login">Login</a>
              </body>
            </html>
        """,
        "https://example.com/docs/start": """
            <html>
              <head>
                <title>Getting Started</title>
                <meta name="description" content="Learn how to start building.">
                <link rel="canonical" href="https://example.com/docs/start">
              </head>
              <body>
                <a href="/blog">Blog</a>
              </body>
            </html>
        """,
        "https://example.com/blog": """
            <html>
              <head>
                <title>Blog</title>
                <meta name="description" content="Product updates and tutorials.">
              </head>
              <body></body>
            </html>
        """,
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
        pipeline = GenerationPipeline(client=client)
        result = await pipeline.run(
            "https://example.com/",
            crawl_config=CrawlerConfig(max_depth=2, max_pages=10),
        )

    assert result.normalized_root_url == "https://example.com/"
    assert [url for url, _, _ in result.crawled_pages] == [
        "https://example.com/",
        "https://example.com/docs/start",
        "https://example.com/blog",
    ]
    assert [page.url for page in result.selected_pages] == [
        "https://example.com/",
        "https://example.com/docs/start",
        "https://example.com/blog",
    ]
    assert result.crawl_summary is not None
    assert result.crawl_summary.pages_crawled == 3
    assert result.crawl_summary.depth_reached == 2
    assert result.crawl_summary.crawl_time_seconds >= 0.0
    assert result.selected_pages[1].category == "Documentation"
    assert "## Documentation" in result.llms_txt_markdown
    assert "## Resources" in result.llms_txt_markdown
    assert "- [Getting Started](https://example.com/docs/start): Learn how to start building." in result.llms_txt_markdown


@pytest.mark.anyio
async def test_generation_pipeline_returns_empty_output_when_crawl_finds_no_pages() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=404, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        pipeline = GenerationPipeline(client=client)
        result = await pipeline.run(
            "https://example.com/",
            crawl_config=CrawlerConfig(max_depth=1, max_pages=5),
        )

    assert result.normalized_root_url == "https://example.com/"
    assert result.crawled_pages == []
    assert result.selected_pages == []
    assert result.llms_txt_markdown == "# Website"
    assert result.crawl_summary is not None
    assert result.crawl_summary.pages_crawled == 0
    assert result.crawl_summary.depth_reached == 0


@pytest.mark.anyio
async def test_generation_pipeline_raises_for_interstitial_root_page() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).rstrip("/") == "https://example.com":
            return httpx.Response(
                status_code=200,
                headers={"content-type": "text/html; charset=utf-8"},
                text="""
                    <html>
                      <head><title>Index.html</title></head>
                      <body>
                        <p>JavaScript is disabled. We need to verify that you're not a robot.</p>
                      </body>
                    </html>
                """,
                request=request,
            )

        return httpx.Response(status_code=404, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        pipeline = GenerationPipeline(client=client)
        with pytest.raises(InterstitialPageError):
            await pipeline.run(
                "https://example.com/",
                crawl_config=CrawlerConfig(max_depth=1, max_pages=5),
                force_generate=True,
            )


@pytest.mark.anyio
async def test_generation_pipeline_uses_existing_llms_txt_when_available() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        request_url = str(request.url)
        if request_url == "https://example.com/llms.txt":
            return httpx.Response(
                status_code=200,
                text="# Existing llms.txt",
                request=request,
            )

        return httpx.Response(status_code=404, request=request)

    async def unexpected_crawl_service(*args, **kwargs):
        raise AssertionError("crawl_service should not be called when llms.txt already exists")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        pipeline = GenerationPipeline(client=client, crawl_service=unexpected_crawl_service)
        result = await pipeline.run("https://example.com/")

    assert result.used_existing_llms_txt is True
    assert result.llms_txt_markdown == "# Existing llms.txt"
    assert result.crawled_pages == []
    assert result.selected_pages == []
    assert result.existing_llms_txt_url == "https://example.com/llms.txt"
    assert result.crawl_summary is None


@pytest.mark.anyio
async def test_generation_pipeline_prefers_path_local_llms_txt_for_subpath_roots() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        request_url = str(request.url)
        if request_url == "https://example.com/docs/llms.txt":
            return httpx.Response(
                status_code=200,
                text="# Docs llms.txt",
                request=request,
            )
        if request_url == "https://example.com/llms.txt":
            return httpx.Response(
                status_code=200,
                text="# Root llms.txt",
                request=request,
            )

        return httpx.Response(status_code=404, request=request)

    async def unexpected_crawl_service(*args, **kwargs):
        raise AssertionError("crawl_service should not be called when a path-local llms.txt exists")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        pipeline = GenerationPipeline(client=client, crawl_service=unexpected_crawl_service)
        result = await pipeline.run("https://example.com/docs/")

    assert result.used_existing_llms_txt is True
    assert result.llms_txt_markdown == "# Docs llms.txt"
    assert result.existing_llms_txt_url == "https://example.com/docs/llms.txt"
    assert result.crawl_summary is None


@pytest.mark.anyio
async def test_generation_pipeline_can_force_generate_even_when_llms_txt_exists() -> None:
    pages = {
        "https://example.com": """
            <html>
              <head><title>Example Platform</title></head>
              <body><a href="/docs/start">Getting Started</a></body>
            </html>
        """,
        "https://example.com/docs/start": """
            <html>
              <head><title>Getting Started</title></head>
              <body></body>
            </html>
        """,
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        request_url = str(request.url).rstrip("/") or str(request.url)
        if str(request.url) == "https://example.com/llms.txt":
            return httpx.Response(status_code=200, text="# Existing llms.txt", request=request)

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
        pipeline = GenerationPipeline(client=client)
        result = await pipeline.run(
            "https://example.com/",
            crawl_config=CrawlerConfig(max_depth=1, max_pages=10),
            force_generate=True,
        )

    assert result.used_existing_llms_txt is False
    assert [url for url, _, _ in result.crawled_pages] == [
        "https://example.com/",
        "https://example.com/docs/start",
    ]
    assert result.existing_llms_txt_url is None
    assert result.crawl_summary is not None
    assert result.crawl_summary.pages_crawled == 2


@pytest.mark.anyio
async def test_generation_pipeline_can_override_robots_setting_in_crawl_config() -> None:
    captured_config: CrawlerConfig | None = None

    async def stub_crawl_service(
        root_url: str,
        *,
        config: CrawlerConfig,
        client=None,
        progress_callback=None,
    ):
        nonlocal captured_config
        captured_config = config
        return []

    pipeline = GenerationPipeline(crawl_service=stub_crawl_service)
    await pipeline.run(
        "https://example.com/",
        crawl_config=CrawlerConfig(max_depth=3, max_pages=25, respect_robots_txt=True),
        respect_robots_txt=False,
    )

    assert captured_config is not None
    assert captured_config.max_depth == 3
    assert captured_config.max_pages == 25
    assert captured_config.respect_robots_txt is False


@pytest.mark.anyio
async def test_generation_pipeline_can_override_sitemap_setting_in_crawl_config() -> None:
    captured_config: CrawlerConfig | None = None

    async def stub_crawl_service(
        root_url: str,
        *,
        config: CrawlerConfig,
        client=None,
        progress_callback=None,
    ):
        nonlocal captured_config
        captured_config = config
        return []

    pipeline = GenerationPipeline(crawl_service=stub_crawl_service)
    await pipeline.run(
        "https://example.com/",
        crawl_config=CrawlerConfig(max_depth=3, max_pages=25, use_sitemap=True),
        use_sitemap=False,
    )

    assert captured_config is not None
    assert captured_config.max_depth == 3
    assert captured_config.max_pages == 25
    assert captured_config.use_sitemap is False


@pytest.mark.anyio
async def test_generation_pipeline_logs_existing_llms_txt_usage(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/llms.txt":
            return httpx.Response(status_code=200, text="# Existing llms.txt", request=request)

        return httpx.Response(status_code=404, request=request)

    caplog.set_level(logging.INFO)
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        pipeline = GenerationPipeline(client=client)
        await pipeline.run("https://example.com/")

    assert "Starting generation pipeline for https://example.com/" in caplog.text
    assert "Using existing llms.txt from https://example.com/llms.txt" in caplog.text
    assert "Completed generation pipeline for https://example.com/ in " in caplog.text


@pytest.mark.anyio
async def test_generation_pipeline_logs_generated_output_summary(
    caplog: pytest.LogCaptureFixture,
) -> None:
    pages = {
        "https://example.com": """
            <html>
              <head><title>Example Platform</title></head>
              <body><a href="/docs/start">Getting Started</a></body>
            </html>
        """,
        "https://example.com/docs/start": """
            <html>
              <head><title>Getting Started</title></head>
              <body></body>
            </html>
        """,
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

    caplog.set_level(logging.INFO)
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        pipeline = GenerationPipeline(client=client)
        await pipeline.run(
            "https://example.com/",
            crawl_config=CrawlerConfig(max_depth=1, max_pages=10),
        )

    assert "Starting generation pipeline for https://example.com/" in caplog.text
    assert "Completed generation pipeline for https://example.com/ in " in caplog.text
    assert "with 2 crawled pages and 2 selected pages" in caplog.text
