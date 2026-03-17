"""Shared typing helpers for the web application layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from services.crawler import CrawlProgress
from services.pipeline import GenerationResult

JobStatus = Literal["running", "completed", "failed"]


@dataclass(slots=True)
class GenerationJobState:
    """Tracked progress state for one in-flight generation job."""

    normalized_root_url: str
    status: JobStatus = "running"
    message: str = "Starting generation..."
    depth: int = 0
    pages_visited: int = 0
    pages_queued: int = 0
    error_message: str | None = None

    def apply_crawl_progress(self, progress: CrawlProgress) -> None:
        """Update the stored job state from a crawler progress event."""

        self.message = f"Crawling {progress.root_url}"
        self.depth = progress.depth
        self.pages_visited = progress.pages_visited
        self.pages_queued = progress.pages_queued

    def to_payload(self, *, result_path: str | None = None) -> dict[str, object]:
        """Return a JSON-serializable snapshot for the polling endpoint."""

        payload: dict[str, object] = {
            "status": self.status,
            "message": self.message,
            "depth": self.depth,
            "pages_visited": self.pages_visited,
            "pages_queued": self.pages_queued,
        }
        if self.error_message:
            payload["error_message"] = self.error_message
        if result_path is not None:
            payload["result_path"] = result_path
        return payload



class PipelineRunner(Protocol):
    """Minimal protocol for objects that can run the generation pipeline."""

    async def run(
        self,
        root_url: str,
        *,
        crawl_config=None,
        force_generate: bool = False,
        respect_robots_txt: bool = True,
        progress_callback=None,
    ) -> GenerationResult:
        """Execute the generation pipeline for the provided URL."""
        ...
