"""Shared typing helpers for the web application layer."""

from __future__ import annotations

from typing import Protocol

from services.pipeline import GenerationResult


class PipelineRunner(Protocol):
    """Minimal protocol for objects that can run the generation pipeline."""

    async def run(
        self,
        root_url: str,
        *,
        crawl_config=None,
        force_generate: bool = False,
        respect_robots_txt: bool = True,
    ) -> GenerationResult:
        """Execute the generation pipeline for the provided URL."""
        ...
