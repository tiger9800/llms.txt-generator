"""Crawler service for discovering internal site pages."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from time import perf_counter
from typing import TypeAlias

import httpx
from bs4 import BeautifulSoup

from utils.http_utils import DEFAULT_USER_AGENT, get_async_client
from utils.robots import RobotsPolicy, load_robots_policy
from utils.sitemap import load_sitemap_urls
from utils.url_utils import canonicalize_same_domain_url, is_html_like_url, is_same_domain, normalize_url, should_skip_url

CrawledPage: TypeAlias = tuple[str, str, int]
ProgressCallback: TypeAlias = Callable[["CrawlProgress"], None]
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CrawlProgress:
    """Progress snapshot emitted while crawling a site."""

    root_url: str
    depth: int
    pages_visited: int
    pages_queued: int


@dataclass(slots=True)
class CrawlerConfig:
    """Configuration values controlling crawl scope and timeouts."""

    max_depth: int = 2
    max_pages: int = 50
    max_concurrent_requests: int = 5
    respect_robots_txt: bool = True
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
    progress_callback: ProgressCallback | None = None,
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
        robots_policy = await _load_crawl_robots_policy(
            normalized_start_url,
            active_client,
            respect_robots_txt=crawler_config.respect_robots_txt,
        )
        if robots_policy is None:
            return []

        sitemap_seed_urls = await load_sitemap_urls(normalized_start_url, active_client)
        crawled_pages = await _crawl_with_client(
            normalized_start_url,
            crawler_config,
            active_client,
            robots_policy,
            sitemap_seed_urls=sitemap_seed_urls,
            progress_callback=progress_callback,
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
    robots_policy: RobotsPolicy,
    *,
    sitemap_seed_urls: list[str],
    progress_callback: ProgressCallback | None,
) -> list[CrawledPage]:
    queue, seen_urls = _initialize_queue(start_url, sitemap_seed_urls)
    crawled_pages: list[CrawledPage] = []
    semaphore = asyncio.Semaphore(config.max_concurrent_requests)

    _emit_progress(
        progress_callback,
        CrawlProgress(
            root_url=start_url,
            depth=0,
            pages_visited=0,
            pages_queued=len(queue),
        ),
    )

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
                if not _should_enqueue_discovered_url(
                    discovered_url,
                    seen_urls=seen_urls,
                    robots_policy=robots_policy,
                ):
                    continue

                seen_urls.add(discovered_url)
                queue.append((discovered_url, depth + 1))

            _emit_progress(
                progress_callback,
                CrawlProgress(
                    root_url=start_url,
                    depth=depth,
                    pages_visited=len(crawled_pages),
                    pages_queued=len(queue),
                ),
            )

    return crawled_pages


def _initialize_queue(
    start_url: str,
    sitemap_seed_urls: list[str],
) -> tuple[deque[tuple[str, int]], set[str]]:
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    seen_urls: set[str] = {start_url}

    for sitemap_url in sitemap_seed_urls:
        normalized_sitemap_url = canonicalize_same_domain_url(sitemap_url, start_url)
        if normalized_sitemap_url == start_url:
            continue

        if not _should_enqueue_url(normalized_sitemap_url, start_url):
            continue

        if normalized_sitemap_url in seen_urls:
            continue

        seen_urls.add(normalized_sitemap_url)
        queue.append((normalized_sitemap_url, 1))

    return queue, seen_urls


async def _fetch_html(url: str, client: httpx.AsyncClient) -> str | None:
    try:
        response = await client.get(url, headers={"User-Agent": DEFAULT_USER_AGENT})
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


async def _load_crawl_robots_policy(
    start_url: str,
    client: httpx.AsyncClient,
    *,
    respect_robots_txt: bool,
) -> RobotsPolicy | None:
    if not respect_robots_txt:
        logger.info("Crawling %s without robots.txt enforcement.", start_url)
        return RobotsPolicy(parser=None)

    robots_policy = await load_robots_policy(start_url, client)
    if robots_policy.allows(start_url):
        return robots_policy

    logger.info("Skipping crawl for %s because robots.txt disallows it.", start_url)
    return None


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

        normalized_candidate = canonicalize_same_domain_url(normalized_candidate, root_url)

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


def _should_enqueue_discovered_url(
    candidate_url: str,
    *,
    seen_urls: set[str],
    robots_policy: RobotsPolicy,
) -> bool:
    if candidate_url in seen_urls:
        return False

    if not robots_policy.allows(candidate_url):
        logger.info("Skipping %s because robots.txt disallows it.", candidate_url)
        return False

    return True


def _is_html_response(response: httpx.Response) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    return "text/html" in content_type or "application/xhtml+xml" in content_type


def _emit_progress(
    progress_callback: ProgressCallback | None,
    progress: CrawlProgress,
) -> None:
    if progress_callback is None:
        return

    progress_callback(progress)
