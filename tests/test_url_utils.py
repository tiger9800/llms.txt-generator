from __future__ import annotations

import pytest

from utils.url_utils import (
    canonicalize_same_domain_url,
    get_url_path,
    is_html_like_url,
    is_same_domain,
    normalize_url,
    should_skip_url,
    url_path_depth,
)


def test_normalize_url_resolves_relative_urls_and_removes_noise() -> None:
    normalized_url = normalize_url(
        "/Docs/Start/?utm_source=newsletter&b=2&a=1#overview",
        base_url="HTTPS://WWW.Example.com",
    )

    assert normalized_url == "https://www.example.com/Docs/Start?a=1&b=2"


def test_normalize_url_can_drop_all_query_parameters() -> None:
    normalized_url = normalize_url(
        "https://example.com/docs/start/?page=1&utm_campaign=spring",
        keep_query=False,
    )

    assert normalized_url == "https://example.com/docs/start"


def test_normalize_url_rejects_empty_values() -> None:
    with pytest.raises(ValueError, match="empty"):
        normalize_url("   ")


def test_is_same_domain_treats_www_as_the_same_site() -> None:
    assert is_same_domain("https://www.example.com/docs", "https://example.com")
    assert not is_same_domain("https://blog.example.com/docs", "https://example.com")


def test_canonicalize_same_domain_url_rewrites_to_origin_host() -> None:
    assert canonicalize_same_domain_url(
        "https://www.example.com/docs/start",
        "https://example.com/",
    ) == "https://example.com/docs/start"


def test_is_html_like_url_filters_common_binary_assets() -> None:
    assert is_html_like_url("https://example.com/docs/start")
    assert not is_html_like_url("https://example.com/files/guide.pdf")
    assert not is_html_like_url("mailto:help@example.com")


def test_should_skip_url_rejects_auth_and_query_heavy_pages() -> None:
    assert should_skip_url("https://example.com/login")
    assert should_skip_url("https://example.com/search?q=llms&page=2&sort=asc&lang=en")
    assert not should_skip_url("https://example.com/docs/getting-started")


def test_url_path_helpers_return_normalized_results() -> None:
    url = "https://example.com/docs/start/"

    assert get_url_path(url) == "/docs/start"
    assert url_path_depth(url) == 2
