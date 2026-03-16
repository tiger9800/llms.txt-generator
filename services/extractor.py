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
        title_text = _normalize_block_text(title_tag.get_text(" ", strip=True))
        cleaned_title_text = _clean_title_text(title_text)
        if cleaned_title_text:
            return cleaned_title_text

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
    content_root = soup.find(["main", "article"]) or soup.body or soup
    text_chunks = _extract_content_text_chunks(content_root)

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


def _extract_content_text_chunks(content_root: Tag | BeautifulSoup) -> list[str]:
    block_text_chunks = [
        text
        for text in (
            _normalize_block_text(block.get_text(" ", strip=True))
            for block in content_root.find_all(["p", "li", "dd"])
        )
        if _is_useful_text_chunk(text)
    ]
    if block_text_chunks:
        return _deduplicate_chunks(block_text_chunks)

    fallback_chunks: list[str] = []
    for element in content_root.find_all(string=True):
        parent = element.parent
        if parent is None or parent.name in {
            "head",
            "header",
            "footer",
            "nav",
            "script",
            "style",
            "noscript",
            "title",
        }:
            continue

        text = _normalize_block_text(str(element))
        if _is_useful_text_chunk(text):
            fallback_chunks.append(text)

    return _deduplicate_chunks(fallback_chunks)


def _normalize_block_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _is_useful_text_chunk(text: str) -> bool:
    if not text or text.lower() in {"html", "body"}:
        return False
    if len(text) < 25:
        return False

    word_count = len(text.split())
    if word_count < 5:
        return False

    return True


def _deduplicate_chunks(text_chunks: list[str]) -> list[str]:
    deduplicated_chunks: list[str] = []
    seen_chunks: set[str] = set()

    for text in text_chunks:
        normalized_text = text.lower()
        if normalized_text in seen_chunks:
            continue

        seen_chunks.add(normalized_text)
        deduplicated_chunks.append(text)

    return deduplicated_chunks


def _clean_title_text(title_text: str) -> str:
    if "<" not in title_text and ">" not in title_text:
        return title_text

    reparsed_text = BeautifulSoup(title_text, "html.parser").get_text(" ", strip=True)
    normalized_reparsed_text = _normalize_block_text(reparsed_text)
    if "<" not in normalized_reparsed_text and ">" not in normalized_reparsed_text:
        return normalized_reparsed_text

    leading_text, _, _ = normalized_reparsed_text.partition("<")
    return _normalize_block_text(leading_text)
