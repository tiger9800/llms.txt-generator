"""Shared page model used throughout the generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from urllib.parse import urlsplit


@dataclass(slots=True)
class Page:
    """Structured representation of a crawled page."""

    url: str
    title: str
    description: str
    path: str
    depth: int
    canonical_url: str | None = None
    score: float = 0.0
    category: str | None = None

    def __post_init__(self) -> None:
        self.url = self._normalize_text(self.url)
        self.title = self._normalize_text(self.title)
        self.description = self._normalize_text(self.description)
        self.path = self._normalize_path(self.path, self.url)
        self.canonical_url = self._normalize_optional_text(self.canonical_url)
        self.category = self._normalize_optional_text(self.category)

        if not self.url:
            raise ValueError("Page URL cannot be empty.")

        if self.depth < 0:
            raise ValueError("Page depth cannot be negative.")

        if not isfinite(self.score):
            raise ValueError("Page score must be a finite number.")

    @property
    def effective_url(self) -> str:
        """Return the canonical URL when available, otherwise the fetched URL."""

        return self.canonical_url or self.url

    @property
    def is_homepage(self) -> bool:
        """Return whether this page points to the site root."""

        return self.path == "/"

    @property
    def path_depth(self) -> int:
        """Return the number of non-empty segments in the page path."""

        if self.path == "/":
            return 0

        return len([segment for segment in self.path.split("/") if segment])

    @staticmethod
    def _normalize_text(value: str) -> str:
        """Collapse surrounding whitespace while preserving the inner content."""

        return value.strip()

    @staticmethod
    def _normalize_path(path: str, url: str) -> str:
        """Return a stable slash-prefixed path for the page."""

        candidate_path = path.strip() or urlsplit(url).path or "/"

        if not candidate_path.startswith("/"):
            candidate_path = f"/{candidate_path}"

        if candidate_path != "/":
            candidate_path = candidate_path.rstrip("/")

        return candidate_path or "/"

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None
