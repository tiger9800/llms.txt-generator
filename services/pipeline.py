"""Generation pipeline orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import logging
from time import perf_counter
from urllib.parse import urljoin, urlsplit
from typing import Awaitable

import httpx

from models.page import Page
from services.crawler import CrawlProgress, CrawledPage, CrawlerConfig, ProgressCallback, crawl_site
from services.extractor import detect_interstitial_page, extract_pages
from services.generator import generate_llms_txt
from services.prioritizer import prioritize_pages
from utils.http_utils import get_async_client
from utils.url_utils import normalize_url

CrawlService = Callable[
    [str],
    Awaitable[list[CrawledPage]],
]
logger = logging.getLogger(__name__)


class InterstitialPageError(RuntimeError):
    """Raised when the root page appears to be an anti-bot or interstitial response."""


@dataclass(slots=True)
class CrawlSummary:
    """Compact crawl statistics for display in the UI."""

    pages_crawled: int
    depth_reached: int
    crawl_time_seconds: float


@dataclass(slots=True)
class GenerationResult:
    """Structured result returned by the generation pipeline."""

    normalized_root_url: str
    crawled_pages: list[CrawledPage]
    selected_pages: list[Page]
    llms_txt_markdown: str
    used_existing_llms_txt: bool = False
    existing_llms_txt_url: str | None = None
    crawl_summary: CrawlSummary | None = None


class GenerationPipeline:
    """Coordinate crawl, extraction, prioritization, and llms.txt generation."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        crawl_service: Callable[..., Awaitable[list[CrawledPage]]] = crawl_site,
        extract_service: Callable[[list[CrawledPage]], list[Page]] = extract_pages,
        prioritize_service: Callable[[list[Page]], list[Page]] = prioritize_pages,
        generate_service: Callable[[list[Page]], str] = generate_llms_txt,
    ) -> None:
        self._client = client
        self._crawl_service = crawl_service
        self._extract_service = extract_service
        self._prioritize_service = prioritize_service
        self._generate_service = generate_service

    async def run(
        self,
        root_url: str,
        *,
        crawl_config: CrawlerConfig | None = None,
        force_generate: bool = False,
        respect_robots_txt: bool = True,
        use_sitemap: bool = True,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        """Run the full deterministic llms.txt generation pipeline."""

        normalized_root_url = normalize_url(root_url)
        pipeline_started_at = perf_counter()
        logger.info("Starting generation pipeline for %s", normalized_root_url)
        existing_llms_txt_result = await self._fetch_existing_llms_txt(normalized_root_url)
        if existing_llms_txt_result is not None and not force_generate:
            existing_llms_txt_url, existing_llms_txt = existing_llms_txt_result
            result = GenerationResult(
                normalized_root_url=normalized_root_url,
                crawled_pages=[],
                selected_pages=[],
                llms_txt_markdown=existing_llms_txt,
                used_existing_llms_txt=True,
                existing_llms_txt_url=existing_llms_txt_url,
            )
            logger.info("Using existing llms.txt from %s", existing_llms_txt_url)
            _log_pipeline_completion(normalized_root_url, result, perf_counter() - pipeline_started_at)
            return result

        crawler_config = (
            CrawlerConfig(respect_robots_txt=respect_robots_txt, use_sitemap=use_sitemap)
            if crawl_config is None
            else replace(crawl_config, respect_robots_txt=respect_robots_txt, use_sitemap=use_sitemap)
        )
        crawl_started_at = perf_counter()
        crawled_pages = await self._crawl_service(
            normalized_root_url,
            config=crawler_config,
            client=self._client,
            progress_callback=progress_callback,
        )
        _raise_if_root_page_is_interstitial(normalized_root_url, crawled_pages)
        crawl_summary = CrawlSummary(
            pages_crawled=len(crawled_pages),
            depth_reached=max((depth for _, _, depth in crawled_pages), default=0),
            crawl_time_seconds=perf_counter() - crawl_started_at,
        )
        extracted_pages = self._extract_service(crawled_pages)
        selected_pages = self._prioritize_service(extracted_pages)
        llms_txt_markdown = self._generate_service(selected_pages)

        result = GenerationResult(
            normalized_root_url=normalized_root_url,
            crawled_pages=crawled_pages,
            selected_pages=selected_pages,
            llms_txt_markdown=llms_txt_markdown,
            existing_llms_txt_url=None,
            crawl_summary=crawl_summary,
        )
        _log_pipeline_completion(normalized_root_url, result, perf_counter() - pipeline_started_at)
        return result

    async def _fetch_existing_llms_txt(self, root_url: str) -> tuple[str, str] | None:
        async with get_async_client(self._client, follow_redirects=True, timeout=10.0) as client:
            for llms_txt_url in _candidate_llms_txt_urls(root_url):
                llms_txt = await _fetch_llms_txt_with_client(client, llms_txt_url)
                if llms_txt is not None:
                    return llms_txt_url, llms_txt

        return None


async def _fetch_llms_txt_with_client(
    client: httpx.AsyncClient,
    llms_txt_url: str,
) -> str | None:
    try:
        response = await client.get(llms_txt_url)
    except httpx.HTTPError:
        return None

    if response.status_code != 200:
        return None

    return response.text


def _candidate_llms_txt_urls(root_url: str) -> list[str]:
    split_result = urlsplit(root_url)
    normalized_path = split_result.path.rstrip("/")
    domain_root_url = urljoin(root_url, "/llms.txt")

    if not normalized_path:
        return [domain_root_url]

    path_local_url = f"{root_url.rstrip('/')}/llms.txt"
    if path_local_url == domain_root_url:
        return [domain_root_url]

    return [path_local_url, domain_root_url]


def _log_pipeline_completion(
    normalized_root_url: str,
    result: GenerationResult,
    elapsed_seconds: float,
) -> None:
    logger.info(
        "Completed generation pipeline for %s in %.3fs with %d crawled pages and %d selected pages",
        normalized_root_url,
        elapsed_seconds,
        len(result.crawled_pages),
        len(result.selected_pages),
    )


def _raise_if_root_page_is_interstitial(
    normalized_root_url: str,
    crawled_pages: list[CrawledPage],
) -> None:
    root_page = next(
        (
            (url, html)
            for url, html, depth in crawled_pages
            if depth == 0 and url == normalized_root_url
        ),
        None,
    )
    if root_page is None:
        return

    _, root_html = root_page
    interstitial_reason = detect_interstitial_page(root_html)
    if interstitial_reason is None:
        return

    raise InterstitialPageError(
        "This site appears to be blocked by bot protection or a JavaScript-only interstitial page."
    )
