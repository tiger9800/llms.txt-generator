"""Route handlers for the llms.txt generator application."""

from __future__ import annotations

import asyncio
from collections.abc import MutableMapping
from uuid import uuid4

from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse

from app.types import GenerationJobState, PipelineRunner
from app.views import render_home_page, render_progress_page, render_result_page
from services.pipeline import GenerationResult, InterstitialPageError
from utils.url_utils import normalize_url


def register_routes(
    rt,
    *,
    pipeline: PipelineRunner,
    progress_store: MutableMapping[str, GenerationJobState],
    result_store: dict[str, GenerationResult],
) -> None:
    """Register the minimal FastHTML routes for the llms.txt generator."""

    @rt("/")
    def get():
        return render_home_page()

    @rt("/generate", methods=["POST"])
    async def post(
        url: str,
        force_generate: str | None = None,
        respect_robots_txt: str | None = None,
    ):
        should_force_generate = force_generate is not None
        should_respect_robots_txt = respect_robots_txt is not None

        try:
            normalized_url = normalize_url(url)
        except ValueError:
            return render_home_page(
                url_value=url,
                error_message="Please enter a valid absolute http(s) URL.",
                force_generate=should_force_generate,
                respect_robots_txt=should_respect_robots_txt,
            )

        job_id = uuid4().hex
        progress_store[job_id] = GenerationJobState(
            normalized_root_url=normalized_url,
            message=f"Crawling {normalized_url}",
            pages_queued=1,
        )
        asyncio.create_task(
            _run_generation_job(
                job_id,
                pipeline=pipeline,
                progress_store=progress_store,
                result_store=result_store,
                normalized_url=normalized_url,
                force_generate=should_force_generate,
                respect_robots_txt=should_respect_robots_txt,
            )
        )
        return render_progress_page(
            normalized_url=normalized_url,
            progress_path=f"/progress/{job_id}",
        )

    @rt("/progress/{job_id}")
    def progress(job_id: str):
        job_state = progress_store.get(job_id)
        if job_state is None:
            return JSONResponse({"status": "failed", "error_message": "Progress state not found."}, status_code=404)

        result_path = f"/result/{job_id}" if job_state.status == "completed" else None
        return JSONResponse(job_state.to_payload(result_path=result_path))

    @rt("/result/{job_id}")
    def result(job_id: str):
        result = result_store.get(job_id)
        if result is None:
            return RedirectResponse(url="/", status_code=303)

        return render_result_page(result, download_path=f"/download/{job_id}")

    @rt("/download/{job_id}")
    def download(job_id: str):
        result = result_store.get(job_id)
        if result is None:
            return RedirectResponse(url="/", status_code=303)

        return PlainTextResponse(
            result.llms_txt_markdown,
            media_type="text/plain; charset=utf-8",
            headers={"content-disposition": 'attachment; filename="llms.txt"'},
        )


async def _run_generation_job(
    job_id: str,
    *,
    pipeline: PipelineRunner,
    progress_store: MutableMapping[str, GenerationJobState],
    result_store: dict[str, GenerationResult],
    normalized_url: str,
    force_generate: bool,
    respect_robots_txt: bool,
) -> None:
    job_state = progress_store[job_id]

    def handle_progress(progress) -> None:
        current_job_state = progress_store.get(job_id)
        if current_job_state is None:
            return

        current_job_state.apply_crawl_progress(progress)

    try:
        result = await pipeline.run(
            normalized_url,
            force_generate=force_generate,
            respect_robots_txt=respect_robots_txt,
            progress_callback=handle_progress,
        )
    except InterstitialPageError as error:
        job_state.status = "failed"
        job_state.error_message = str(error)
        job_state.message = "Generation failed."
        return
    except Exception:
        job_state.status = "failed"
        job_state.error_message = "Something went wrong while crawling that site. Please try again."
        job_state.message = "Generation failed."
        return

    result_store[job_id] = result
    job_state.status = "completed"
    job_state.message = "Generation complete."
