"""Generation pipeline orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin
from typing import Awaitable

import httpx

from models.page import Page
from services.crawler import CrawledPage, CrawlerConfig, crawl_site
from services.extractor import extract_pages
from services.generator import generate_llms_txt
from services.prioritizer import prioritize_pages
from utils.http_utils import get_async_client
from utils.url_utils import normalize_url

CrawlService = Callable[
    [str],
    Awaitable[list[CrawledPage]],
]


@dataclass(slots=True)
class GenerationResult:
    """Structured result returned by the generation pipeline."""

    normalized_root_url: str
    crawled_pages: list[CrawledPage]
    selected_pages: list[Page]
    llms_txt_markdown: str
    used_existing_llms_txt: bool = False
    existing_llms_txt_url: str | None = None


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
        force_regenerate: bool = False,
    ) -> GenerationResult:
        """Run the full deterministic llms.txt generation pipeline."""

        normalized_root_url = normalize_url(root_url)
        existing_llms_txt = await self._fetch_existing_llms_txt(normalized_root_url)
        if existing_llms_txt is not None and not force_regenerate:
            return GenerationResult(
                normalized_root_url=normalized_root_url,
                crawled_pages=[],
                selected_pages=[],
                llms_txt_markdown=existing_llms_txt,
                used_existing_llms_txt=True,
                existing_llms_txt_url=urljoin(normalized_root_url, "/llms.txt"),
            )

        crawler_config = crawl_config or CrawlerConfig()
        crawled_pages = await self._crawl_service(
            normalized_root_url,
            config=crawler_config,
            client=self._client,
        )
        extracted_pages = self._extract_service(crawled_pages)
        selected_pages = self._prioritize_service(extracted_pages)
        llms_txt_markdown = self._generate_service(selected_pages)

        return GenerationResult(
            normalized_root_url=normalized_root_url,
            crawled_pages=crawled_pages,
            selected_pages=selected_pages,
            llms_txt_markdown=llms_txt_markdown,
            existing_llms_txt_url=urljoin(normalized_root_url, "/llms.txt"),
        )

    async def _fetch_existing_llms_txt(self, root_url: str) -> str | None:
        llms_txt_url = urljoin(root_url, "/llms.txt")

        async with get_async_client(self._client, follow_redirects=True, timeout=10.0) as client:
            return await _fetch_llms_txt_with_client(client, llms_txt_url)


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
