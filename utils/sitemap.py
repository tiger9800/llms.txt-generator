"""Helpers for discovering and parsing sitemap URLs."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from urllib.parse import urljoin
from xml.etree import ElementTree

import httpx

from utils.http_utils import DEFAULT_USER_AGENT
from utils.url_utils import normalize_url

logger = logging.getLogger(__name__)


async def load_sitemap_urls(
    root_url: str,
    client: httpx.AsyncClient,
    *,
    max_urls: int,
) -> list[str]:
    """Return normalized page URLs discovered from the site's sitemap hints."""

    if max_urls <= 0:
        return []

    sitemap_urls = [urljoin(root_url, "/sitemap.xml")]
    sitemap_urls.extend(await _load_robots_sitemap_urls(root_url, client))

    seen_sitemap_urls: set[str] = set()
    discovered_page_urls: list[str] = []
    seen_page_urls: set[str] = set()

    for sitemap_url in sitemap_urls:
        await _collect_sitemap_urls(
            sitemap_url,
            client,
            seen_sitemap_urls=seen_sitemap_urls,
            discovered_page_urls=discovered_page_urls,
            seen_page_urls=seen_page_urls,
            max_urls=max_urls,
        )

        if len(discovered_page_urls) >= max_urls:
            break

    return discovered_page_urls


async def _load_robots_sitemap_urls(root_url: str, client: httpx.AsyncClient) -> list[str]:
    robots_url = urljoin(root_url, "/robots.txt")

    try:
        response = await client.get(robots_url, headers={"User-Agent": DEFAULT_USER_AGENT})
    except httpx.HTTPError:
        return []

    if response.status_code != 200:
        return []

    declared_sitemap_urls: list[str] = []
    for line in response.text.splitlines():
        stripped_line = line.strip()
        if not stripped_line.lower().startswith("sitemap:"):
            continue

        _, raw_sitemap_url = stripped_line.split(":", 1)
        sitemap_candidate = raw_sitemap_url.strip()
        if not sitemap_candidate:
            continue

        try:
            declared_sitemap_urls.append(normalize_url(sitemap_candidate, base_url=root_url))
        except ValueError:
            logger.debug("Skipping invalid sitemap declaration %r from %s", sitemap_candidate, robots_url)

    return declared_sitemap_urls


async def _collect_sitemap_urls(
    sitemap_url: str,
    client: httpx.AsyncClient,
    *,
    seen_sitemap_urls: set[str],
    discovered_page_urls: list[str],
    seen_page_urls: set[str],
    max_urls: int,
) -> None:
    if len(discovered_page_urls) >= max_urls:
        return

    normalized_sitemap_url = normalize_url(sitemap_url)
    if normalized_sitemap_url in seen_sitemap_urls:
        return

    seen_sitemap_urls.add(normalized_sitemap_url)

    try:
        response = await client.get(normalized_sitemap_url, headers={"User-Agent": DEFAULT_USER_AGENT})
    except httpx.HTTPError:
        logger.debug("Failed to fetch sitemap %s", normalized_sitemap_url)
        return

    if response.status_code != 200:
        logger.debug("No usable sitemap at %s (status %d)", normalized_sitemap_url, response.status_code)
        return

    try:
        document_root = ElementTree.fromstring(response.text)
    except ElementTree.ParseError:
        logger.debug("Failed to parse sitemap XML from %s", normalized_sitemap_url)
        return

    root_tag_name = _strip_namespace(document_root.tag)
    if root_tag_name == "urlset":
        _add_sitemap_page_urls(
            _extract_loc_values(document_root),
            discovered_page_urls=discovered_page_urls,
            seen_page_urls=seen_page_urls,
            max_urls=max_urls,
        )
        return

    if root_tag_name == "sitemapindex":
        for nested_sitemap_url in _extract_loc_values(document_root):
            if len(discovered_page_urls) >= max_urls:
                break

            await _collect_sitemap_urls(
                nested_sitemap_url,
                client,
                seen_sitemap_urls=seen_sitemap_urls,
                discovered_page_urls=discovered_page_urls,
                seen_page_urls=seen_page_urls,
                max_urls=max_urls,
            )


def _add_sitemap_page_urls(
    page_urls: Iterable[str],
    *,
    discovered_page_urls: list[str],
    seen_page_urls: set[str],
    max_urls: int,
) -> None:
    for page_url in page_urls:
        if len(discovered_page_urls) >= max_urls:
            break

        try:
            normalized_page_url = normalize_url(page_url)
        except ValueError:
            continue

        if normalized_page_url in seen_page_urls:
            continue

        seen_page_urls.add(normalized_page_url)
        discovered_page_urls.append(normalized_page_url)


def _extract_loc_values(document_root: ElementTree.Element) -> list[str]:
    loc_values: list[str] = []

    for element in document_root.iter():
        if _strip_namespace(element.tag) != "loc":
            continue

        if element.text is None:
            continue

        loc_value = element.text.strip()
        if loc_value:
            loc_values.append(loc_value)

    return loc_values


def _strip_namespace(tag_name: str) -> str:
    if "}" not in tag_name:
        return tag_name

    return tag_name.rsplit("}", 1)[-1]
