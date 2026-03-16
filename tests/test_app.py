from __future__ import annotations

from dataclasses import dataclass

from fasthtml.core import Client

from app.main import create_app
from models.page import Page
from services.pipeline import GenerationResult


@dataclass
class StubPipeline:
    result: GenerationResult

    async def run(self, root_url: str, *, crawl_config=None):
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


def test_generate_route_renders_result_preview_and_download_link() -> None:
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
    )
    app = create_app(pipeline=StubPipeline(result=result))
    client = Client(app)
    response = client.post("/generate", data={"url": "https://example.com/"})  # type: ignore[attr-defined]

    assert response.status_code == 200
    assert "llms.txt Preview" in response.text
    assert "Crawled pages:" in response.text
    assert "Selected pages:" in response.text
    assert "Download llms.txt" in response.text
    assert "Getting Started" in response.text


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

    response = client.post("/generate", data={"url": "not-a-url"})  # type: ignore[attr-defined]

    assert response.status_code == 200
    assert "Please enter a valid absolute http(s) URL." in response.text


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
