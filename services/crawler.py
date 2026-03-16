"""Crawler service for discovering internal site pages."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from time import perf_counter
from typing import TypeAlias

import httpx
from bs4 import BeautifulSoup

from utils.http_utils import get_async_client
from utils.url_utils import is_html_like_url, is_same_domain, normalize_url, should_skip_url

CrawledPage: TypeAlias = tuple[str, str, int]
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CrawlerConfig:
    """Configuration values controlling crawl scope and timeouts."""

    max_depth: int = 2
    max_pages: int = 50
    max_concurrent_requests: int = 5
    timeout: float = 10.0

    def __post_init__(self) -> None:
        if self.max_depth < 0:
            raise ValueError("max_depth must be greater than or equal to zero.")
        if self.max_pages <= 0:
            raise ValueError("max_pages must be greater than zero.")
        if self.max_concurrent_requests <= 0:
            raise ValueError("max_concurrent_requests must be greater than zero.")
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than zero.")


async def crawl_site(
    start_url: str,
    *,
    config: CrawlerConfig | None = None,
    client: httpx.AsyncClient | None = None,
) -> list[CrawledPage]:
    """Breadth-first crawl of HTML pages within the start URL's domain."""

    crawler_config = config or CrawlerConfig()
    normalized_start_url = normalize_url(start_url)
    crawl_started_at = perf_counter()

    if should_skip_url(normalized_start_url):
        logger.info("Skipping crawl for %s because the URL is filtered.", normalized_start_url)
        return []

    logger.info("Starting crawl for %s", normalized_start_url)

    async with get_async_client(
        client,
        follow_redirects=True,
        timeout=crawler_config.timeout,
    ) as active_client:
        crawled_pages = await _crawl_with_client(
            normalized_start_url,
            crawler_config,
            active_client,
        )
        elapsed_seconds = perf_counter() - crawl_started_at
        logger.info(
            "Completed crawl for %s in %.3fs with %d pages",
            normalized_start_url,
            elapsed_seconds,
            len(crawled_pages),
        )
        return crawled_pages


async def _crawl_with_client(
    start_url: str,
    config: CrawlerConfig,
    client: httpx.AsyncClient,
) -> list[CrawledPage]:
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    seen_urls: set[str] = {start_url}
    crawled_pages: list[CrawledPage] = []
    semaphore = asyncio.Semaphore(config.max_concurrent_requests)

    while queue and len(crawled_pages) < config.max_pages:
        current_level = _pop_current_level(queue)
        fetch_results = await asyncio.gather(
            *[
                _fetch_html_with_limit(url, client, semaphore)
                for url, _depth in current_level
            ]
        )

        for (current_url, depth), html in zip(current_level, fetch_results):
            if len(crawled_pages) >= config.max_pages:
                break

            if depth > config.max_depth or html is None:
                continue

            crawled_pages.append((current_url, html, depth))
            if depth == config.max_depth:
                continue

            for discovered_url in _extract_internal_links(html, current_url, start_url):
                if discovered_url in seen_urls:
                    continue

                seen_urls.add(discovered_url)
                queue.append((discovered_url, depth + 1))

    return crawled_pages


async def _fetch_html(url: str, client: httpx.AsyncClient) -> str | None:
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    if not _is_html_response(response):
        return None

    return response.text


async def _fetch_html_with_limit(
    url: str,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> str | None:
    fetch_started_at = perf_counter()
    async with semaphore:
        html = await _fetch_html(url, client)

    elapsed_seconds = perf_counter() - fetch_started_at
    logger.debug(
        "Fetched %s in %.3fs (%s)",
        url,
        elapsed_seconds,
        "html" if html is not None else "skipped",
    )
    return html


def _pop_current_level(queue: deque[tuple[str, int]]) -> list[tuple[str, int]]:
    current_url, depth = queue.popleft()
    current_level = [(current_url, depth)]

    while queue and queue[0][1] == depth:
        current_level.append(queue.popleft())

    return current_level


def _extract_internal_links(html: str, page_url: str, root_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    internal_links: list[str] = []
    seen_links: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href")
        if not isinstance(href, str):
            continue

        try:
            normalized_candidate = normalize_url(href, base_url=page_url)
        except ValueError:
            continue

        if not _should_enqueue_url(normalized_candidate, root_url):
            continue

        if normalized_candidate in seen_links:
            continue

        seen_links.add(normalized_candidate)
        internal_links.append(normalized_candidate)

    return internal_links


def _should_enqueue_url(candidate_url: str, root_url: str) -> bool:
    return (
        is_same_domain(candidate_url, root_url)
        and is_html_like_url(candidate_url)
        and not should_skip_url(candidate_url)
    )


def _is_html_response(response: httpx.Response) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    return "text/html" in content_type or "application/xhtml+xml" in content_type
