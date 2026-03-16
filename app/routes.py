"""Route handlers for the llms.txt generator application."""

from __future__ import annotations

from uuid import uuid4

from starlette.responses import PlainTextResponse, RedirectResponse

from app.types import PipelineRunner
from app.views import render_home_page, render_result_page
from services.pipeline import GenerationResult
from utils.url_utils import normalize_url


def register_routes(rt, *, pipeline: PipelineRunner, result_store: dict[str, GenerationResult]) -> None:
    """Register the minimal FastHTML routes for the llms.txt generator."""

    @rt("/")
    def get():
        return render_home_page()

    @rt("/generate", methods=["POST"])
    async def post(url: str, force_regenerate: str | None = None):
        try:
            normalized_url = normalize_url(url)
        except ValueError:
            return render_home_page(
                url_value=url,
                error_message="Please enter a valid absolute http(s) URL.",
            )

        try:
            result = await pipeline.run(
                normalized_url,
                force_regenerate=force_regenerate is not None,
            )
        except Exception:
            return render_home_page(
                url_value=normalized_url,
                error_message="Something went wrong while crawling that site. Please try again.",
            )

        result_id = uuid4().hex
        result_store[result_id] = result
        return render_result_page(result, download_path=f"/download/{result_id}")

    @rt("/download/{result_id}")
    def download(result_id: str):
        result = result_store.get(result_id)
        if result is None:
            return RedirectResponse(url="/", status_code=303)

        return PlainTextResponse(
            result.llms_txt_markdown,
            media_type="text/plain; charset=utf-8",
            headers={"content-disposition": 'attachment; filename="llms.txt"'},
        )
