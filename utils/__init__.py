"""Utility helpers shared across the project."""

from .http_utils import get_async_client
from .url_utils import (
    get_url_path,
    is_html_like_url,
    is_same_domain,
    normalize_url,
    should_skip_url,
    url_path_depth,
)

__all__ = [
    "get_async_client",
    "get_url_path",
    "is_html_like_url",
    "is_same_domain",
    "normalize_url",
    "should_skip_url",
    "url_path_depth",
]
