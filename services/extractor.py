"""Metadata extraction helpers for converting HTML into typed page records."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeAlias
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from bs4.element import Tag

from models.page import Page
from utils.url_utils import get_url_path, normalize_url

DEFAULT_DESCRIPTION = "No description available."
FALLBACK_DESCRIPTION_LENGTH = 160
CrawledPageInput: TypeAlias = tuple[str, str, int]


def extract_page(url: str, html: str, depth: int) -> Page:
    """Parse a fetched HTML document into a structured ``Page`` model."""

    normalized_url = normalize_url(url)
    soup = BeautifulSoup(html, "html.parser")

    title = _extract_title(soup, normalized_url)
    description = _extract_description(soup)
    canonical_url = _extract_canonical_url(soup, normalized_url)

    if not description:
        description = _build_fallback_description(soup)

    return Page(
        url=normalized_url,
        title=title,
        description=description,
        path=get_url_path(normalized_url),
        depth=depth,
        canonical_url=canonical_url,
    )


def extract_pages(crawled_pages: Iterable[CrawledPageInput]) -> list[Page]:
    """Convert an iterable of crawled page inputs into structured pages."""

    return [
        extract_page(url=url, html=html, depth=depth)
        for url, html, depth in crawled_pages
    ]


def _extract_title(soup: BeautifulSoup, url: str) -> str:
    title_tag = soup.find("title")
    if isinstance(title_tag, Tag):
        title_text = title_tag.get_text(" ", strip=True)
        if title_text:
            return title_text

    return _build_fallback_title(url)


def _extract_description(soup: BeautifulSoup) -> str | None:
    description_tag = soup.find("meta", attrs={"name": lambda value: _matches_name(value, "description")})
    if isinstance(description_tag, Tag):
        description = description_tag.get("content")
        if isinstance(description, str):
            normalized_description = description.strip()
            if normalized_description:
                return normalized_description

    return None


def _extract_canonical_url(soup: BeautifulSoup, page_url: str) -> str:
    canonical_tag = soup.find("link", attrs={"rel": lambda value: _has_rel(value, "canonical")})
    if isinstance(canonical_tag, Tag):
        href = canonical_tag.get("href")
        if isinstance(href, str) and _is_supported_canonical_href(href):
            try:
                return normalize_url(href, base_url=page_url)
            except ValueError:
                pass

    return page_url


def _build_fallback_title(url: str) -> str:
    path = get_url_path(url)
    if path == "/":
        hostname = urlsplit(url).hostname or "Homepage"
        return hostname.removeprefix("www.").split(".")[0].replace("-", " ").title()

    last_segment = path.split("/")[-1]
    return last_segment.replace("-", " ").replace("_", " ").title()


def _build_fallback_description(soup: BeautifulSoup) -> str:
    text_chunks: list[str] = []

    for element in soup.find_all(string=True):
        parent = element.parent
        if parent is None or parent.name in {"head", "script", "style", "noscript", "title"}:
            continue

        text = " ".join(element.split())
        if text:
            text_chunks.append(text)

    summary = " ".join(text_chunks).strip()
    if not summary:
        return DEFAULT_DESCRIPTION

    if len(summary) <= FALLBACK_DESCRIPTION_LENGTH:
        return summary

    truncated_summary = summary[:FALLBACK_DESCRIPTION_LENGTH].rstrip()
    truncated_summary = truncated_summary.rsplit(" ", 1)[0].rstrip() or truncated_summary
    return f"{truncated_summary}..."


def _matches_name(value: object, expected: str) -> bool:
    return isinstance(value, str) and value.strip().lower() == expected


def _has_rel(value: object, expected: str) -> bool:
    if isinstance(value, str):
        candidates = value.split()
    elif isinstance(value, list):
        candidates = [item for item in value if isinstance(item, str)]
    else:
        return False

    return any(candidate.strip().lower() == expected for candidate in candidates)


def _is_supported_canonical_href(href: str) -> bool:
    normalized_href = href.strip()
    return bool(normalized_href) and not any(character.isspace() for character in normalized_href)
