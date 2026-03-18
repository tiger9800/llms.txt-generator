"""Metadata extraction helpers for converting HTML into typed page records."""

from __future__ import annotations

from collections.abc import Iterable
import re
from typing import TypeAlias
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from bs4.element import Tag

from models.page import Page
from utils.url_utils import get_url_path, normalize_url

DEFAULT_DESCRIPTION = "No description available."
FALLBACK_DESCRIPTION_LENGTH = 160
MAX_DESCRIPTION_LENGTH = 220
CrawledPageInput: TypeAlias = tuple[str, str, int]
INTERSTITIAL_PATTERNS: tuple[str, ...] = (
    "verify that you're not a robot",
    "enable javascript",
    "access denied",
    "captcha",
    "checking your browser",
    "javascript is disabled",
)


def extract_page(url: str, html: str, depth: int) -> Page:
    """Parse a fetched HTML document into a structured ``Page`` model."""

    normalized_url = normalize_url(url)
    soup = BeautifulSoup(html, "html.parser")

    title = _extract_title(soup, normalized_url)
    description = _extract_description(soup)
    canonical_url = _extract_canonical_url(soup, normalized_url)

    if not description:
        description = _build_fallback_description(soup, html)
    else:
        description = _normalize_description(description, max_length=MAX_DESCRIPTION_LENGTH)

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


def detect_interstitial_page(html: str) -> str | None:
    """Return a short reason when HTML appears to be an anti-bot or interstitial page."""

    soup = BeautifulSoup(html, "html.parser")
    page_text = _normalize_block_text(soup.get_text(" ", strip=True)).casefold()
    if not page_text:
        return None

    for pattern in INTERSTITIAL_PATTERNS:
        if pattern in page_text:
            return pattern

    return None


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
            normalized_description = _normalize_block_text(description)
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


def _build_fallback_description(soup: BeautifulSoup, raw_html: str) -> str:
    content_root = soup.find(["main", "article"]) or soup.body or soup
    text_chunks = _extract_content_text_chunks(content_root)
    if not text_chunks:
        raw_body_text = _extract_raw_body_text(raw_html)
        if raw_body_text:
            text_chunks = [raw_body_text]

    summary = " ".join(text_chunks).strip()
    if not summary:
        return DEFAULT_DESCRIPTION

    return _normalize_description(summary, max_length=FALLBACK_DESCRIPTION_LENGTH)


def _normalize_description(description: str, *, max_length: int) -> str:
    normalized_description = _normalize_block_text(description)
    if len(normalized_description) <= max_length:
        return normalized_description

    sentence_truncated_description = _truncate_at_sentence_boundary(normalized_description, max_length=max_length)
    if sentence_truncated_description is not None:
        return sentence_truncated_description

    return _truncate_at_word_boundary(normalized_description, max_length=max_length)


def _truncate_at_sentence_boundary(description: str, *, max_length: int) -> str | None:
    sentence_end_matches = list(re.finditer(r"[.!?](?:\s|$)", description))
    if not sentence_end_matches:
        return None

    sentence_end_positions = [match.end() for match in sentence_end_matches if match.end() <= max_length]
    if not sentence_end_positions:
        return None

    return description[: sentence_end_positions[-1]].rstrip()


def _truncate_at_word_boundary(description: str, *, max_length: int) -> str:
    truncated_description = description[:max_length].rstrip()
    if " " in truncated_description:
        truncated_description = truncated_description.rsplit(" ", 1)[0].rstrip() or truncated_description

    truncated_description = truncated_description.rstrip(",:;/-")
    return f"{truncated_description}..."


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


def _extract_raw_body_text(raw_html: str) -> str | None:
    body_match = re.search(r"<body[^>]*>(.*)", raw_html, flags=re.IGNORECASE | re.DOTALL)
    if body_match is None:
        return None

    body_fragment = body_match.group(1)
    body_text = BeautifulSoup(body_fragment, "html.parser").get_text(" ", strip=True)
    normalized_body_text = _normalize_block_text(body_text)
    if _is_useful_text_chunk(normalized_body_text):
        return normalized_body_text

    return None
