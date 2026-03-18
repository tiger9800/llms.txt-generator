"""Page scoring and selection service."""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from models.page import Page
from utils.url_utils import normalize_url

DEFAULT_MAX_PAGES = 50
HIGH_VALUE_SECTION_SCORES: tuple[tuple[str, str, float], ...] = (
    ("/docs", "Documentation", 5.0),
    ("/api", "Documentation", 5.0),
    ("/guide", "Documentation", 4.0),
    ("/blog", "Resources", 3.5),
    ("/pricing", "Product", 3.0),
    ("/about", "Company", 2.5),
)
PENALIZED_PATH_SEGMENTS: frozenset[str] = frozenset(
    {"login", "auth", "account", "tag", "archive", "filter"}
)


def prioritize_pages(pages: list[Page], *, max_pages: int = DEFAULT_MAX_PAGES) -> list[Page]:
    """Return a deduplicated, scored, and deterministically ordered page list."""

    if max_pages <= 0:
        raise ValueError("max_pages must be greater than zero.")

    unique_pages = _deduplicate_pages(pages)
    scored_pages = [_score_page(page) for page in unique_pages]

    return sorted(
        scored_pages,
        key=lambda page: (
            -page.score,
            page.path_depth,
            page.title.lower(),
            page.effective_url,
        ),
    )[:max_pages]


def _deduplicate_pages(pages: list[Page]) -> list[Page]:
    unique_pages_by_url: dict[str, Page] = {}

    for page in pages:
        page_key = _page_identity(page)
        existing_page = unique_pages_by_url.get(page_key)
        if existing_page is None or _page_quality_key(page) > _page_quality_key(existing_page):
            unique_pages_by_url[page_key] = page

    return list(unique_pages_by_url.values())


def _score_page(page: Page) -> Page:
    score = 0.0
    derived_category, section_boost = _section_boost(page.path)

    if page.is_homepage:
        score += 10.0

    score += max(0.0, 4.0 - float(page.path_depth))
    score += section_boost
    score += _metadata_score(page)
    score -= _path_penalty(page.path)
    score -= _query_penalty(page.effective_url)

    category = page.category or derived_category
    return replace(page, score=score, category=category)


def _section_boost(path: str) -> tuple[str | None, float]:
    normalized_path = path.lower()
    for prefix, category, boost in HIGH_VALUE_SECTION_SCORES:
        if prefix in normalized_path:
            return category, boost

    return None, 0.0


def _metadata_score(page: Page) -> float:
    score = 0.0
    if page.title:
        score += 1.0
    if page.description:
        score += 1.0
    if page.canonical_url:
        score += 0.5
    return score


def _path_penalty(path: str) -> float:
    path_segments = {segment for segment in path.lower().split("/") if segment}
    if path_segments & PENALIZED_PATH_SEGMENTS:
        return 6.0
    return 0.0


def _query_penalty(url: str) -> float:
    query_pairs = parse_qsl(urlsplit(url).query, keep_blank_values=True)
    if not query_pairs:
        return 0.0
    return min(float(len(query_pairs)), 4.0)


def _page_identity(page: Page) -> str:
    normalized_url = normalize_url(page.canonical_url or page.url)
    split_result = urlsplit(normalized_url)
    hostname = (split_result.hostname or "").removeprefix("www.")
    netloc = hostname
    if split_result.port is not None:
        netloc = f"{hostname}:{split_result.port}"

    return urlunsplit(
        (
            split_result.scheme,
            netloc,
            split_result.path,
            split_result.query,
            "",
        )
    )


def _page_quality_key(page: Page) -> tuple[int, int, int, int]:
    return (
        int(bool(page.description)),
        int(bool(page.title)),
        -page.depth,
        -page.path_depth,
    )
