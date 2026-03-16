"""Application entry point for the FastHTML web app."""

from __future__ import annotations

from fasthtml.common import fast_app, serve

from app.routes import register_routes
from app.types import PipelineRunner
from services.pipeline import GenerationPipeline, GenerationResult


__all__ = ["PipelineRunner", "app", "create_app"]


def create_app(*, pipeline: PipelineRunner | None = None):
    """Create the FastHTML app for the llms.txt generator."""

    app, rt = fast_app(title="Automated llms.txt Generator")
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
