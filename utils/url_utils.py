"""Helpers for normalizing and filtering URLs used by the crawler pipeline."""

from __future__ import annotations

from posixpath import normpath
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

TRACKING_QUERY_PARAMETERS: frozenset[str] = frozenset(
    {
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "source",
        "utm_campaign",
        "utm_content",
        "utm_id",
        "utm_medium",
        "utm_name",
        "utm_source",
        "utm_term",
    }
)

NON_HTML_FILE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".7z",
        ".avi",
        ".bmp",
        ".css",
        ".csv",
        ".doc",
        ".docx",
        ".gif",
        ".gz",
        ".ico",
        ".jpeg",
        ".jpg",
        ".js",
        ".json",
        ".mp3",
        ".mp4",
        ".pdf",
        ".png",
        ".ppt",
        ".pptx",
        ".svg",
        ".tar",
        ".tgz",
        ".txt",
        ".wav",
        ".webm",
        ".webp",
        ".xml",
        ".xls",
        ".xlsx",
        ".zip",
    }
)

SKIPPED_PATH_SEGMENTS: frozenset[str] = frozenset(
    {
        "account",
        "admin",
        "auth",
        "cart",
        "checkout",
        "filter",
        "login",
        "logout",
        "register",
        "search",
        "signin",
        "signup",
        "tag",
    }
)


def normalize_url(
    url: str,
    *,
    base_url: str | None = None,
    keep_query: bool = True,
    drop_tracking_params: bool = True,
) -> str:
    """Return a normalized absolute HTTP(S) URL suitable for comparison.

    The normalization rules intentionally keep the URL readable while removing
    common crawler noise such as fragments, duplicate slashes, and tracking
    query parameters.
    """

    raw_url = url.strip()
    if not raw_url:
        raise ValueError("URL cannot be empty.")

    resolved_url = urljoin(base_url, raw_url) if base_url else raw_url
    split_result = urlsplit(resolved_url)

    if not split_result.scheme or not split_result.netloc:
        raise ValueError(f"URL must be absolute after normalization: {url!r}")

    scheme = split_result.scheme.lower()
    hostname = (split_result.hostname or "").lower()
    if not hostname:
        raise ValueError(f"URL host cannot be empty: {url!r}")

    netloc = hostname
    if split_result.port is not None and split_result.port != _default_port_for_scheme(
        scheme
    ):
        netloc = f"{netloc}:{split_result.port}"

    normalized_path = _normalize_path(split_result.path)
    normalized_query = ""
    if keep_query:
        normalized_query = _normalize_query(
            split_result.query,
            drop_tracking_params=drop_tracking_params,
        )

    return urlunsplit((scheme, netloc, normalized_path, normalized_query, ""))


def is_same_domain(candidate_url: str, origin_url: str) -> bool:
    """Return whether two URLs belong to the same crawl domain."""

    candidate_host = _comparable_host(candidate_url)
    origin_host = _comparable_host(origin_url)
    return candidate_host == origin_host


def is_html_like_url(url: str) -> bool:
    """Return whether the URL likely points to an HTML page."""

    split_result = urlsplit(url)
    if split_result.scheme.lower() not in {"http", "https"}:
        return False

    path = split_result.path.lower()
    if not path or path.endswith("/"):
        return True

    return not any(path.endswith(extension) for extension in NON_HTML_FILE_EXTENSIONS)


def should_skip_url(url: str) -> bool:
    """Return whether the crawler should ignore the URL."""

    split_result = urlsplit(url)
    if split_result.scheme.lower() not in {"http", "https"}:
        return True

    if not is_html_like_url(url):
        return True

    path_segments = {
        segment for segment in split_result.path.lower().split("/") if segment
    }
    if path_segments & SKIPPED_PATH_SEGMENTS:
        return True

    query_pairs = parse_qsl(split_result.query, keep_blank_values=True)
    if len(query_pairs) > 3:
        return True

    return False


def get_url_path(url: str) -> str:
    """Return the normalized path component for the given URL."""

    return _normalize_path(urlsplit(url).path)


def url_path_depth(url: str) -> int:
    """Return the number of non-empty path segments in the URL."""

    path = get_url_path(url)
    if path == "/":
        return 0

    return len([segment for segment in path.split("/") if segment])


def _normalize_path(path: str) -> str:
    normalized_path = path or "/"
    normalized_path = normpath(normalized_path)

    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"

    if normalized_path == "/.":
        normalized_path = "/"

    if normalized_path != "/":
        normalized_path = normalized_path.rstrip("/")

    return normalized_path or "/"


def _normalize_query(
    query: str,
    *,
    drop_tracking_params: bool,
) -> str:
    if not query:
        return ""

    normalized_pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        normalized_key = key.strip()
        normalized_value = value.strip()

        if not normalized_key:
            continue

        if drop_tracking_params and normalized_key.lower() in TRACKING_QUERY_PARAMETERS:
            continue

        normalized_pairs.append((normalized_key, normalized_value))

    normalized_pairs.sort()
    return urlencode(normalized_pairs, doseq=True)


def _default_port_for_scheme(scheme: str) -> int | None:
    if scheme == "http":
        return 80
    if scheme == "https":
        return 443
    return None


def _comparable_host(url: str) -> str:
    normalized_url = normalize_url(url, keep_query=False)
    hostname = urlsplit(normalized_url).hostname or ""
    return hostname.removeprefix("www.")
