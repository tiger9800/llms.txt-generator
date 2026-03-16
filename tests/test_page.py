from __future__ import annotations

import math

import pytest

from models.page import Page


def test_page_normalizes_text_and_path() -> None:
    page = Page(
        url=" https://example.com/docs/start/ ",
        title=" Getting Started ",
        description=" Intro to the docs. ",
        path="docs/start/",
        depth=1,
        canonical_url=" ",
        category=" Documentation ",
    )

    assert page.url == "https://example.com/docs/start/"
    assert page.title == "Getting Started"
    assert page.description == "Intro to the docs."
    assert page.path == "/docs/start"
    assert page.canonical_url is None
    assert page.category == "Documentation"


def test_page_falls_back_to_path_from_url() -> None:
    page = Page(
        url="https://example.com/blog/post-one/",
        title="Post One",
        description="A blog post.",
        path="",
        depth=2,
    )

    assert page.path == "/blog/post-one"
    assert page.path_depth == 2
    assert not page.is_homepage


def test_page_uses_canonical_url_when_available() -> None:
    page = Page(
        url="https://example.com/docs/start",
        title="Getting Started",
        description="Intro to the docs.",
        path="/docs/start",
        depth=1,
        canonical_url="https://docs.example.com/start",
    )

    assert page.effective_url == "https://docs.example.com/start"


@pytest.mark.parametrize("depth", [-1, -5])
def test_page_rejects_negative_depth(depth: int) -> None:
    with pytest.raises(ValueError, match="depth"):
        Page(
            url="https://example.com",
            title="Example",
            description="Example site.",
            path="/",
            depth=depth,
        )


def test_page_rejects_non_finite_score() -> None:
    with pytest.raises(ValueError, match="finite"):
        Page(
            url="https://example.com",
            title="Example",
            description="Example site.",
            path="/",
            depth=0,
            score=math.inf,
        )
