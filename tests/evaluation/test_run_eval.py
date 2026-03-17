from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from models.page import Page
from services.pipeline import GenerationResult
from tests.evaluation.run_eval import (
    EvalMetrics,
    compare_llms_txt,
    evaluate_site,
    format_eval_error,
    format_eval_report,
    load_eval_sites,
    main,
    parse_llms_txt,
)


def test_parse_llms_txt_extracts_sections_and_entries() -> None:
    markdown = """# Example

> Example summary

## Documentation
- [Getting Started](https://example.com/docs/start): Learn how to start building.

## Company
- [About](https://example.com/about)
"""

    entries = parse_llms_txt(markdown)

    assert [entry.section for entry in entries] == ["Documentation", "Company"]
    assert entries[0].title == "Getting Started"
    assert entries[0].description == "Learn how to start building."
    assert entries[1].url == "https://example.com/about"
    assert entries[1].description is None


def test_compare_llms_txt_reports_overlap_and_coverage() -> None:
    generated_markdown = """# Example

## Documentation
- [Getting Started](https://example.com/docs/start): Learn how to start building.
- [API](https://example.com/api)
"""
    existing_markdown = """# Example

## Documentation
- [Getting Started](https://example.com/docs/start): Learn how to start building.

## Company
- [About](https://example.com/about): Learn about Example.
"""

    metrics = compare_llms_txt(generated_markdown, existing_markdown)

    assert metrics == EvalMetrics(
        generated_url_count=2,
        existing_url_count=2,
        overlap_url_count=1,
        generated_slug_count=2,
        existing_slug_count=2,
        overlap_slug_count=1,
        generated_title_count=2,
        existing_title_count=2,
        overlap_title_count=1,
        precision=0.5,
        recall=0.5,
        slug_precision=0.5,
        slug_recall=0.5,
        title_precision=0.5,
        title_recall=0.5,
        generated_description_coverage=0.5,
        existing_description_coverage=1.0,
        section_similarity=0.5,
    )


def test_compare_llms_txt_normalizes_display_title_suffixes() -> None:
    generated_markdown = """# Example

## Documentation
- [Actions in ChatKit | OpenAI API](https://example.com/chatkit-actions)
- [FastHTML By Example – fasthtml](https://example.com/by-example)
"""
    existing_markdown = """# Example

## Documentation
- [Actions in ChatKit](https://example.com/other-chatkit-actions)
- [FastHTML By Example](https://example.com/other-by-example)
"""

    metrics = compare_llms_txt(generated_markdown, existing_markdown)

    assert metrics.overlap_url_count == 0
    assert metrics.overlap_slug_count == 0
    assert metrics.overlap_title_count == 2
    assert metrics.slug_precision == 0.0
    assert metrics.slug_recall == 0.0
    assert metrics.title_precision == 1.0
    assert metrics.title_recall == 1.0


def test_compare_llms_txt_normalizes_markdown_escapes_and_colon_suffixes() -> None:
    generated_markdown = """# Example

## Documentation
- [AI subtitling at Scale at SVT in Sweden : Limecraft](https://example.com/limecraft)
- [Documentary & Unscripted Entertainment](https://example.com/documentary)
"""
    existing_markdown = """# Example

## Documentation
- [AI subtitling at Scale at SVT in Sweden](https://example.com/other-limecraft)
- [Documentary \\& Unscripted Entertainment](https://example.com/other-documentary)
"""

    metrics = compare_llms_txt(generated_markdown, existing_markdown)

    assert metrics.overlap_url_count == 0
    assert metrics.overlap_slug_count == 0
    assert metrics.overlap_title_count == 2
    assert metrics.title_precision == 1.0
    assert metrics.title_recall == 1.0


def test_compare_llms_txt_reports_slug_overlap_for_markdown_twins() -> None:
    generated_markdown = """# Example

## Documentation
- [Quickstart](https://example.com/docs/quickstart)
- [Index](https://example.com/docs/index.html)
"""
    existing_markdown = """# Example

## Documentation
- [Quickstart](https://example.com/docs/quickstart.md)
- [Index](https://example.com/docs/index.md)
"""

    metrics = compare_llms_txt(generated_markdown, existing_markdown)

    assert metrics.overlap_url_count == 0
    assert metrics.overlap_slug_count == 2
    assert metrics.slug_precision == 1.0
    assert metrics.slug_recall == 1.0


def test_load_eval_sites_reads_checked_in_urls(tmp_path: Path) -> None:
    sites_file = tmp_path / "sites.txt"
    sites_file.write_text(
        "\n".join(
            [
                "# Sample sites",
                "https://fastht.ml/docs/",
                "",
                "https://llmstxt.org/",
                "https://developers.openai.com/api/docs/",
            ]
        ),
        encoding="utf-8",
    )

    sites = load_eval_sites(sites_file)

    assert sites == [
        "https://fastht.ml/docs",
        "https://llmstxt.org/",
        "https://developers.openai.com/api/docs",
    ]


@pytest.mark.anyio
async def test_evaluate_site_runs_pipeline_and_fetches_existing_llms_txt() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/llms.txt":
            return httpx.Response(
                status_code=200,
                text="""# Example

## Documentation
- [Getting Started](https://example.com/docs/start): Learn how to start building.
""",
                request=request,
            )

        return httpx.Response(status_code=404, request=request)

    class StubPipeline:
        async def run(self, root_url: str, *, force_generate: bool = True, respect_robots_txt: bool = True):
            assert root_url == "https://example.com/"
            assert force_generate is True
            assert respect_robots_txt is True
            return GenerationResult(
                normalized_root_url=root_url,
                crawled_pages=[],
                selected_pages=[
                    Page(
                        url="https://example.com/docs/start",
                        title="Getting Started",
                        description="Learn how to start building.",
                        path="/docs/start",
                        depth=1,
                    )
                ],
                llms_txt_markdown="""# Example

## Documentation
- [Getting Started](https://example.com/docs/start): Learn how to start building.
""",
            )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        report = await evaluate_site(
            "https://example.com/",
            pipeline=StubPipeline(),
            client=client,
        )

    assert report.root_url == "https://example.com/"
    assert report.existing_llms_txt_url == "https://example.com/llms.txt"
    assert report.metrics.overlap_url_count == 1
    assert report.metrics.overlap_slug_count == 1
    assert report.metrics.overlap_title_count == 1
    assert report.metrics.precision == 1.0
    assert report.metrics.recall == 1.0
    assert "Precision: 100.00%" in format_eval_report(report)
    assert "Slug precision: 100.00%" in format_eval_report(report)
    assert "Title precision: 100.00%" in format_eval_report(report)
    assert report.existing_markdown.startswith("# Example")


def test_format_eval_error_renders_error_block() -> None:
    formatted_error = format_eval_error(
        "https://example.com/",
        ValueError("No existing llms.txt found."),
    )

    assert "Root URL: https://example.com/" in formatted_error
    assert "Status: ERROR" in formatted_error
    assert "No existing llms.txt found." in formatted_error


def test_format_eval_report_includes_title_diff_samples() -> None:
    report = type("Report", (), {})()
    report.root_url = "https://example.com/"
    report.existing_llms_txt_url = "https://example.com/llms.txt"
    report.existing_markdown = "# Existing"
    report.generated_result = GenerationResult(
        normalized_root_url="https://example.com/",
        crawled_pages=[],
        selected_pages=[],
        llms_txt_markdown="# Generated",
    )
    report.metrics = EvalMetrics(
        generated_url_count=2,
        existing_url_count=2,
        overlap_url_count=0,
        generated_slug_count=2,
        existing_slug_count=2,
        overlap_slug_count=1,
        generated_title_count=2,
        existing_title_count=2,
        overlap_title_count=1,
        precision=0.0,
        recall=0.0,
        slug_precision=0.5,
        slug_recall=0.5,
        title_precision=0.5,
        title_recall=0.5,
        generated_description_coverage=1.0,
        existing_description_coverage=1.0,
        section_similarity=0.0,
    )
    report.generated_only_titles = ["Generated Only"]
    report.existing_only_titles = ["Existing Only"]

    formatted_report = format_eval_report(report)

    assert "Slug overlap: 1" in formatted_report
    assert "Title overlap: 1" in formatted_report
    assert "Sample generated-only titles:" in formatted_report
    assert "- Generated Only" in formatted_report
    assert "Sample existing-only titles:" in formatted_report
    assert "- Existing Only" in formatted_report


def test_format_eval_report_can_show_all_diffs() -> None:
    report = type("Report", (), {})()
    report.root_url = "https://example.com/"
    report.existing_llms_txt_url = "https://example.com/llms.txt"
    report.existing_markdown = "# Existing"
    report.generated_result = GenerationResult(
        normalized_root_url="https://example.com/",
        crawled_pages=[],
        selected_pages=[],
        llms_txt_markdown="# Generated",
    )
    report.metrics = EvalMetrics(
        generated_url_count=6,
        existing_url_count=6,
        overlap_url_count=0,
        generated_slug_count=6,
        existing_slug_count=6,
        overlap_slug_count=0,
        generated_title_count=6,
        existing_title_count=6,
        overlap_title_count=0,
        precision=0.0,
        recall=0.0,
        slug_precision=0.0,
        slug_recall=0.0,
        title_precision=0.0,
        title_recall=0.0,
        generated_description_coverage=1.0,
        existing_description_coverage=1.0,
        section_similarity=0.0,
    )
    report.generated_only_titles = [f"Generated {index}" for index in range(6)]
    report.existing_only_titles = [f"Existing {index}" for index in range(6)]

    formatted_report = format_eval_report(report, show_all_diffs=True)

    assert "Generated-only titles:" in formatted_report
    assert "Sample generated-only titles:" not in formatted_report
    assert "- Generated 5" in formatted_report
    assert "Existing-only titles:" in formatted_report
    assert "Sample existing-only titles:" not in formatted_report
    assert "- Existing 5" in formatted_report


@pytest.mark.anyio
async def test_format_eval_report_can_include_markdown_bodies() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/llms.txt":
            return httpx.Response(
                status_code=200,
                text="# Existing\n\n## Docs\n- [Start](https://example.com/docs/start): Existing description.",
                request=request,
            )

        return httpx.Response(status_code=404, request=request)

    class StubPipeline:
        async def run(self, root_url: str, *, force_generate: bool = True, respect_robots_txt: bool = True):
            return GenerationResult(
                normalized_root_url=root_url,
                crawled_pages=[],
                selected_pages=[],
                llms_txt_markdown="# Generated\n\n## Docs\n- [Start](https://example.com/docs/start): Generated description.",
            )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        report = await evaluate_site(
            "https://example.com/",
            pipeline=StubPipeline(),
            client=client,
        )

    formatted_report = format_eval_report(report, show_markdown=True)

    assert "Generated Markdown:" in formatted_report
    assert "# Generated" in formatted_report
    assert "Existing Markdown:" in formatted_report
    assert "# Existing" in formatted_report


def test_main_continues_when_one_site_fails(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    async def fake_evaluate_site(root_url: str, **_: object) -> object:
        if root_url == "https://bad.example/":
            raise ValueError("No existing llms.txt found.")

        class _Report:
            pass

        report = _Report()
        report.root_url = root_url
        report.existing_llms_txt_url = f"{root_url}llms.txt"
        report.existing_markdown = "# Existing"
        report.generated_result = GenerationResult(
            normalized_root_url=root_url,
            crawled_pages=[],
            selected_pages=[],
            llms_txt_markdown="# Generated",
        )
        report.metrics = EvalMetrics(
            generated_url_count=1,
            existing_url_count=1,
            overlap_url_count=1,
            generated_slug_count=1,
            existing_slug_count=1,
            overlap_slug_count=1,
            generated_title_count=1,
            existing_title_count=1,
            overlap_title_count=1,
            precision=1.0,
            recall=1.0,
            slug_precision=1.0,
            slug_recall=1.0,
            title_precision=1.0,
            title_recall=1.0,
            generated_description_coverage=1.0,
            existing_description_coverage=1.0,
            section_similarity=1.0,
        )
        report.generated_only_titles = []
        report.existing_only_titles = []
        return report

    monkeypatch.setattr("tests.evaluation.run_eval.load_eval_sites", lambda: ["https://bad.example/", "https://good.example/"])
    monkeypatch.setattr("tests.evaluation.run_eval.evaluate_site", fake_evaluate_site)

    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Root URL: https://bad.example/" in captured.out
    assert "Status: ERROR" in captured.out
    assert "Root URL: https://good.example/" in captured.out


def test_main_can_show_markdown(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    async def fake_evaluate_site(root_url: str, **_: object) -> object:
        class _Report:
            pass

        report = _Report()
        report.root_url = root_url
        report.existing_llms_txt_url = f"{root_url}llms.txt"
        report.existing_markdown = "# Existing"
        report.generated_result = GenerationResult(
            normalized_root_url=root_url,
            crawled_pages=[],
            selected_pages=[],
            llms_txt_markdown="# Generated",
        )
        report.metrics = EvalMetrics(
            generated_url_count=1,
            existing_url_count=1,
            overlap_url_count=1,
            generated_slug_count=1,
            existing_slug_count=1,
            overlap_slug_count=1,
            generated_title_count=1,
            existing_title_count=1,
            overlap_title_count=1,
            precision=1.0,
            recall=1.0,
            slug_precision=1.0,
            slug_recall=1.0,
            title_precision=1.0,
            title_recall=1.0,
            generated_description_coverage=1.0,
            existing_description_coverage=1.0,
            section_similarity=1.0,
        )
        report.generated_only_titles = []
        report.existing_only_titles = []
        return report

    monkeypatch.setattr("tests.evaluation.run_eval.load_eval_sites", lambda: ["https://good.example/"])
    monkeypatch.setattr("tests.evaluation.run_eval.evaluate_site", fake_evaluate_site)

    exit_code = main(["--show-markdown"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Generated Markdown:" in captured.out
    assert "# Generated" in captured.out
    assert "Existing Markdown:" in captured.out
    assert "# Existing" in captured.out


def test_main_can_show_all_diffs(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    async def fake_evaluate_site(root_url: str, **_: object) -> object:
        class _Report:
            pass

        report = _Report()
        report.root_url = root_url
        report.existing_llms_txt_url = f"{root_url}llms.txt"
        report.existing_markdown = "# Existing"
        report.generated_result = GenerationResult(
            normalized_root_url=root_url,
            crawled_pages=[],
            selected_pages=[],
            llms_txt_markdown="# Generated",
        )
        report.metrics = EvalMetrics(
            generated_url_count=1,
            existing_url_count=1,
            overlap_url_count=0,
            generated_slug_count=6,
            existing_slug_count=6,
            overlap_slug_count=0,
            generated_title_count=6,
            existing_title_count=6,
            overlap_title_count=0,
            precision=0.0,
            recall=0.0,
            slug_precision=0.0,
            slug_recall=0.0,
            title_precision=0.0,
            title_recall=0.0,
            generated_description_coverage=1.0,
            existing_description_coverage=1.0,
            section_similarity=0.0,
        )
        report.generated_only_titles = [f"Generated {index}" for index in range(6)]
        report.existing_only_titles = [f"Existing {index}" for index in range(6)]
        return report

    monkeypatch.setattr("tests.evaluation.run_eval.load_eval_sites", lambda: ["https://good.example/"])
    monkeypatch.setattr("tests.evaluation.run_eval.evaluate_site", fake_evaluate_site)

    exit_code = main(["--show-all-diffs"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Generated-only titles:" in captured.out
    assert "- Generated 5" in captured.out
    assert "Existing-only titles:" in captured.out
    assert "- Existing 5" in captured.out
