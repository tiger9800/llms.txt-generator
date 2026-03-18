from __future__ import annotations

from models.page import Page
from services.prioritizer import prioritize_pages


def test_prioritize_pages_boosts_homepage_and_shallow_high_value_paths() -> None:
    pages = [
        Page(
            url="https://example.com/",
            title="Example",
            description="Platform overview.",
            path="/",
            depth=0,
        ),
        Page(
            url="https://example.com/docs/start",
            title="Getting Started",
            description="Start here.",
            path="/docs/start",
            depth=1,
        ),
        Page(
            url="https://example.com/blog",
            title="Blog",
            description="Product updates.",
            path="/blog",
            depth=1,
        ),
    ]

    prioritized_pages = prioritize_pages(pages)

    assert [page.url for page in prioritized_pages] == [
        "https://example.com/",
        "https://example.com/docs/start",
        "https://example.com/blog",
    ]
    assert prioritized_pages[1].category == "Documentation"
    assert prioritized_pages[2].category == "Resources"


def test_prioritize_pages_penalizes_auth_and_query_heavy_urls() -> None:
    pages = [
        Page(
            url="https://example.com/docs/api",
            title="API",
            description="API docs.",
            path="/docs/api",
            depth=1,
        ),
        Page(
            url="https://example.com/account/login?next=%2Fdocs&page=1&source=nav",
            title="Login",
            description="Log in.",
            path="/account/login",
            depth=1,
        ),
    ]

    prioritized_pages = prioritize_pages(pages)

    assert prioritized_pages[0].url == "https://example.com/docs/api"
    assert prioritized_pages[-1].url == "https://example.com/account/login?next=%2Fdocs&page=1&source=nav"


def test_prioritize_pages_deduplicates_by_canonical_url() -> None:
    pages = [
        Page(
            url="https://example.com/docs/start?utm_source=newsletter",
            title="Getting Started",
            description="Start here.",
            path="/docs/start",
            depth=1,
            canonical_url="https://example.com/docs/start",
        ),
        Page(
            url="https://example.com/docs/start",
            title="Getting Started",
            description="",
            path="/docs/start",
            depth=2,
        ),
    ]

    prioritized_pages = prioritize_pages(pages)

    assert len(prioritized_pages) == 1
    assert prioritized_pages[0].effective_url == "https://example.com/docs/start"
    assert prioritized_pages[0].description == "Start here."


def test_prioritize_pages_deduplicates_www_and_non_www_variants() -> None:
    pages = [
        Page(
            url="https://example.com/about",
            title="About",
            description="About the company.",
            path="/about",
            depth=1,
        ),
        Page(
            url="https://www.example.com/about",
            title="About",
            description="",
            path="/about",
            depth=2,
        ),
    ]

    prioritized_pages = prioritize_pages(pages)

    assert len(prioritized_pages) == 1
    assert prioritized_pages[0].url == "https://example.com/about"


def test_prioritize_pages_respects_max_pages() -> None:
    pages = [
        Page(
            url="https://example.com/",
            title="Example",
            description="Overview.",
            path="/",
            depth=0,
        ),
        Page(
            url="https://example.com/docs",
            title="Docs",
            description="Docs overview.",
            path="/docs",
            depth=1,
        ),
        Page(
            url="https://example.com/about",
            title="About",
            description="About us.",
            path="/about",
            depth=1,
        ),
    ]

    prioritized_pages = prioritize_pages(pages, max_pages=2)

    assert len(prioritized_pages) == 2
    assert [page.url for page in prioritized_pages] == [
        "https://example.com/",
        "https://example.com/docs",
    ]


def test_prioritize_pages_marks_a_small_lower_ranked_tail_as_optional() -> None:
    pages = [
        Page(
            url="https://example.com/",
            title="Example",
            description="Overview.",
            path="/",
            depth=0,
        ),
        Page(
            url="https://example.com/docs",
            title="Docs",
            description="Docs overview.",
            path="/docs",
            depth=1,
        ),
        Page(
            url="https://example.com/api",
            title="API",
            description="API reference.",
            path="/api",
            depth=1,
        ),
        Page(
            url="https://example.com/blog",
            title="Blog",
            description="Updates.",
            path="/blog",
            depth=1,
        ),
        Page(
            url="https://example.com/about",
            title="About",
            description="About us.",
            path="/about",
            depth=1,
        ),
    ]

    prioritized_pages = prioritize_pages(pages)

    assert prioritized_pages[0].is_optional is False
    assert [page.url for page in prioritized_pages if page.is_optional] == [
        "https://example.com/about",
    ]


def test_prioritize_pages_omits_optional_for_small_page_sets() -> None:
    pages = [
        Page(
            url="https://example.com/",
            title="Example",
            description="Overview.",
            path="/",
            depth=0,
        ),
        Page(
            url="https://example.com/docs",
            title="Docs",
            description="Docs overview.",
            path="/docs",
            depth=1,
        ),
        Page(
            url="https://example.com/api",
            title="API",
            description="API reference.",
            path="/api",
            depth=1,
        ),
        Page(
            url="https://example.com/blog",
            title="Blog",
            description="Updates.",
            path="/blog",
            depth=1,
        ),
    ]

    prioritized_pages = prioritize_pages(pages)

    assert all(not page.is_optional for page in prioritized_pages)
