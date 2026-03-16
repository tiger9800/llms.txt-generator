"""Application entry point for the FastHTML web app."""

from __future__ import annotations

import logging

from fasthtml.common import Link, fast_app, serve

from app.routes import register_routes
from app.types import PipelineRunner
from services.pipeline import GenerationPipeline, GenerationResult


__all__ = ["PipelineRunner", "app", "create_app"]
FAVICON_PATH = "/static/logo.png"


def _configure_logging() -> None:
    """Configure simple console logging for local app runs."""

    if logging.getLogger().handlers:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def create_app(*, pipeline: PipelineRunner | None = None):
    """Create the FastHTML app for the llms.txt generator."""

    _configure_logging()
    app, rt = fast_app(
        title="Automated llms.txt Generator",
        hdrs=(Link(rel="icon", href=FAVICON_PATH, type="image/png"),),
    )
    result_store: dict[str, GenerationResult] = {}
    register_routes(
        rt,
        pipeline=pipeline or GenerationPipeline(),
        result_store=result_store,
    )
    return app


app = create_app()


if __name__ == "__main__":
    serve(appname="app.main")
