from __future__ import annotations

from dataclasses import dataclass
import json
import re
import time

from fasthtml.core import Client

from app.main import create_app
from models.page import Page
from services.crawler import CrawlProgress
from services.crawler import CrawlerConfig
from services.pipeline import CrawlSummary, GenerationResult, InterstitialPageError


@dataclass
class StubPipeline:
    result: GenerationResult
    last_force_generate: bool = False
    last_respect_robots_txt: bool = True
    last_crawl_config: CrawlerConfig | None = None
    emitted_progress: bool = False

    async def run(
        self,
        root_url: str,
        *,
        crawl_config=None,
        force_generate: bool = False,
        respect_robots_txt: bool = True,
        progress_callback=None,
    ):
        self.last_force_generate = force_generate
        self.last_respect_robots_txt = respect_robots_txt
        self.last_crawl_config = crawl_config
        if progress_callback is not None:
            progress_callback(
                CrawlProgress(
                    root_url=root_url,
                    depth=1,
                    pages_visited=2,
                    pages_queued=3,
                )
            )
            self.emitted_progress = True
        return self.result


def test_home_route_renders_url_form() -> None:
    app = create_app(
        pipeline=StubPipeline(
            result=GenerationResult(
                normalized_root_url="https://example.com/",
                crawled_pages=[],
                selected_pages=[],
                llms_txt_markdown="# Website",
            )
        )
    )
    client = Client(app)
    response = client.get("/")

    assert response.status_code == 200
    assert '<form' in response.text
    assert 'action="/generate"' in response.text
    assert 'method="post"' in response.text
    assert 'name="url"' in response.text
    assert 'name="respect_robots_txt"' in response.text
    assert "Advanced crawl options" in response.text
    assert 'name="max_depth"' in response.text
    assert 'name="max_pages"' in response.text
    assert 'name="request_timeout"' in response.text
    assert 'name="max_concurrency"' in response.text
    assert 'rel="icon"' in response.text
    assert 'href="/static/logo.png"' in response.text


def test_generate_route_renders_progress_page_and_result_preview() -> None:
    result = GenerationResult(
        normalized_root_url="https://example.com/",
        crawled_pages=[
            ("https://example.com/", "<html></html>", 0),
            ("https://example.com/docs/start", "<html></html>", 1),
        ],
        selected_pages=[
            Page(
                url="https://example.com/",
                title="Example Platform",
                description="Developer tools and docs for Example Platform.",
                path="/",
                depth=0,
            ),
            Page(
                url="https://example.com/docs/start",
                title="Getting Started",
                description="Learn how to start building.",
                path="/docs/start",
                depth=1,
                category="Documentation",
                score=10.0,
            ),
        ],
        llms_txt_markdown="# Example Platform\n\n## Documentation\n- [Getting Started](https://example.com/docs/start): Learn how to start building.",
        crawl_summary=CrawlSummary(
            pages_crawled=2,
            depth_reached=1,
            crawl_time_seconds=0.42,
        ),
    )
    stub_pipeline = StubPipeline(result=result)
    app = create_app(pipeline=stub_pipeline)
    client = Client(app)
    response = client.post("/generate", data={"url": "https://example.com/"})  # type: ignore[attr-defined]

    assert response.status_code == 200
    assert "Generating llms.txt" in response.text
    assert "Crawling and generating llms.txt..." in response.text
    assert "Pages visited:" in response.text
    assert '/progress/' in response.text
    assert "@keyframes spin" in response.text

    job_id = _extract_job_id(response.text)
    progress_payload = _wait_for_progress_completion(client, job_id)

    assert progress_payload["status"] == "completed"
    assert progress_payload["result_path"] == f"/result/{job_id}"
    assert stub_pipeline.emitted_progress is True
    assert stub_pipeline.last_crawl_config == CrawlerConfig()

    result_response = client.get(f"/result/{job_id}")

    assert result_response.status_code == 200
    assert "Automated llms.txt Generator" in result_response.text
    assert "Generation Summary" in result_response.text
    assert "Generated llms.txt" in result_response.text
    assert "Crawled pages:" in result_response.text
    assert "Selected pages:" in result_response.text
    assert "Crawl Summary" in result_response.text
    assert "Pages crawled:" in result_response.text
    assert "Depth reached:" in result_response.text
    assert "Total crawl time:" in result_response.text
    assert "Copy llms.txt" in result_response.text
    assert 'id="llms-txt-preview"' in result_response.text
    assert "copyLlmsTxt()" in result_response.text
    assert "Download llms.txt" in result_response.text
    assert "Getting Started" in result_response.text


def test_generate_route_can_disable_robots_txt_respect() -> None:
    stub_pipeline = StubPipeline(
        result=GenerationResult(
            normalized_root_url="https://example.com/",
            crawled_pages=[],
            selected_pages=[],
            llms_txt_markdown="# Website",
        )
    )
    app = create_app(pipeline=stub_pipeline)
    client = Client(app)

    response = client.post(
        "/generate",
        data={
            "url": "https://example.com/",
            "max_depth": "3",
            "max_pages": "25",
            "request_timeout": "12.5",
            "max_concurrency": "4",
        },
    )  # type: ignore[attr-defined]

    assert response.status_code == 200
    assert stub_pipeline.last_force_generate is False
    assert stub_pipeline.last_respect_robots_txt is False
    assert stub_pipeline.last_crawl_config == CrawlerConfig(
        max_depth=3,
        max_pages=25,
        timeout=12.5,
        max_concurrent_requests=4,
    )


def test_generate_route_shows_friendly_error_for_invalid_url() -> None:
    app = create_app(
        pipeline=StubPipeline(
            result=GenerationResult(
                normalized_root_url="https://example.com/",
                crawled_pages=[],
                selected_pages=[],
                llms_txt_markdown="# Website",
            )
        )
    )
    client = Client(app)

    response = client.post(
        "/generate",
        data={"url": "not-a-url", "respect_robots_txt": "1"},
    )  # type: ignore[attr-defined]

    assert response.status_code == 200
    assert "Please enter a valid absolute http(s) URL." in response.text


def test_generate_route_shows_friendly_error_for_invalid_advanced_crawl_settings() -> None:
    app = create_app(
        pipeline=StubPipeline(
            result=GenerationResult(
                normalized_root_url="https://example.com/",
                crawled_pages=[],
                selected_pages=[],
                llms_txt_markdown="# Website",
            )
        )
    )
    client = Client(app)

    response = client.post(
        "/generate",
        data={
            "url": "https://example.com/",
            "max_depth": "9",
            "max_pages": "50",
            "request_timeout": "10.0",
            "max_concurrency": "5",
            "respect_robots_txt": "1",
        },
    )  # type: ignore[attr-defined]

    assert response.status_code == 200
    assert "Invalid advanced crawl options:" in response.text


def test_download_route_redirects_when_result_is_missing() -> None:
    app = create_app(
        pipeline=StubPipeline(
            result=GenerationResult(
                normalized_root_url="https://example.com/",
                crawled_pages=[],
                selected_pages=[],
                llms_txt_markdown="# Website",
            )
        )
    )
    client = Client(app)

    response = client.get("/download/missing")

    assert response.status_code == 303


def test_download_route_uses_website_specific_filename() -> None:
    app = create_app(
        pipeline=StubPipeline(
            result=GenerationResult(
                normalized_root_url="https://www.example.com/docs/api/",
                crawled_pages=[],
                selected_pages=[],
                llms_txt_markdown="# Website",
            )
        )
    )
    client = Client(app)

    response = client.post("/generate", data={"url": "https://www.example.com/docs/api/"})  # type: ignore[attr-defined]
    job_id = _extract_job_id(response.text)
    _wait_for_progress_completion(client, job_id)

    download_response = client.get(f"/download/{job_id}")

    assert download_response.status_code == 200
    assert download_response.headers["content-disposition"] == (
        'attachment; filename="example-com-docs-api-llms.txt"'
    )


def test_progress_route_reports_failure_for_missing_job() -> None:
    app = create_app(
        pipeline=StubPipeline(
            result=GenerationResult(
                normalized_root_url="https://example.com/",
                crawled_pages=[],
                selected_pages=[],
                llms_txt_markdown="# Website",
            )
        )
    )
    client = Client(app)

    response = client.get("/progress/missing")
    payload = json.loads(response.text)

    assert response.status_code == 404
    assert payload["status"] == "failed"


def test_generate_route_shows_interstitial_detection_message() -> None:
    @dataclass
    class InterstitialPipeline:
        async def run(
            self,
            root_url: str,
            *,
            crawl_config=None,
            force_generate: bool = False,
            respect_robots_txt: bool = True,
            progress_callback=None,
        ):
            raise InterstitialPageError(
                "This site appears to be blocked by bot protection or a JavaScript-only interstitial page."
            )

    app = create_app(pipeline=InterstitialPipeline())
    client = Client(app)

    response = client.post("/generate", data={"url": "https://example.com/"})  # type: ignore[attr-defined]
    job_id = _extract_job_id(response.text)
    failure_payload = _wait_for_failed_progress(client, job_id)

    assert failure_payload["status"] == "failed"
    assert "bot protection" in failure_payload["error_message"]


def test_favicon_asset_is_served() -> None:
    app = create_app(
        pipeline=StubPipeline(
            result=GenerationResult(
                normalized_root_url="https://example.com/",
                crawled_pages=[],
                selected_pages=[],
                llms_txt_markdown="# Website",
            )
        )
    )
    client = Client(app)

    response = client.get("/static/logo.png")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")


def _extract_job_id(html: str) -> str:
    job_match = re.search(r"/progress/([0-9a-f]+)", html)
    assert job_match is not None
    return job_match.group(1)


def _wait_for_progress_completion(client: Client, job_id: str) -> dict[str, object]:
    for _ in range(10):
        response = client.get(f"/progress/{job_id}")
        payload = json.loads(response.text)
        if payload.get("status") == "completed":
            return payload
        time.sleep(0.01)

    raise AssertionError("Generation job did not complete in time for the test.")


def _wait_for_failed_progress(client: Client, job_id: str) -> dict[str, object]:
    for _ in range(10):
        response = client.get(f"/progress/{job_id}")
        payload = json.loads(response.text)
        if payload.get("status") == "failed":
            return payload
        time.sleep(0.01)

    raise AssertionError("Generation job did not fail in time for the test.")
