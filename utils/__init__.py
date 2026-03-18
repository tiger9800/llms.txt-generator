"""Utility helpers shared across the project."""

from .http_utils import DEFAULT_USER_AGENT, get_async_client
from .robots import RobotsPolicy, load_robots_policy
from .sitemap import load_sitemap_urls
from .url_utils import (
    canonicalize_same_domain_url,
    get_url_path,
    is_html_like_url,
    is_same_domain,
    normalize_url,
    should_skip_url,
    url_path_depth,
)

__all__ = [
    "DEFAULT_USER_AGENT",
    "canonicalize_same_domain_url",
    "get_async_client",
    "get_url_path",
    "is_html_like_url",
    "is_same_domain",
    "load_robots_policy",
    "load_sitemap_urls",
    "normalize_url",
    "RobotsPolicy",
    "should_skip_url",
    "url_path_depth",
]
