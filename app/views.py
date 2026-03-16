"""Reusable view helpers and UI fragments."""

from __future__ import annotations

from fasthtml.common import Button, Div, Form, H1, H2, Input, Li, P, Pre, Strong, Titled, Ul

from services.pipeline import GenerationResult


def render_home_page(*, url_value: str = "", error_message: str | None = None):
    """Render the home page with the generation form and optional error state."""

    form = Form(
        P("Enter a public website URL to generate a preview of its llms.txt file."),
        Input(
            type="url",
            name="url",
            value=url_value,
            placeholder="https://example.com",
            required=True,
        ),
        Div(
            Input(
                type="checkbox",
                name="force_generate",
                value="1",
                id="force_generate",
            ),
            "Force generate even if llms.txt exists",
            style="margin-top: 1rem;",
        ),
        Div(Button("Generate llms.txt", type="submit"), style="margin-top: 1rem;"),
        action="/generate",
        method="post",
    )

    error_block = ()
    if error_message:
        error_block = (
            Div(
                Strong("We couldn't generate an llms.txt file."),
                P(error_message),
                style="padding: 1rem; border: 1px solid #d9534f; margin: 1rem 0;",
            ),
        )

    return Titled(
        "Automated llms.txt Generator",
        Div(
            H1("Automated llms.txt Generator"),
            *error_block,
            form,
            style="max-width: 48rem; margin: 2rem auto; padding: 0 1rem;",
        ),
    )


def render_result_page(result: GenerationResult, *, download_path: str):
    """Render the result page with crawl summary and llms.txt preview."""

    summary = Ul(
        Li(Strong("Normalized URL: "), result.normalized_root_url),
        Li(
            Strong("Source: "),
            "Existing llms.txt" if result.used_existing_llms_txt else "Generated from crawl",
        ),
        Li(Strong("Crawled pages: "), str(len(result.crawled_pages))),
        Li(Strong("Selected pages: "), str(len(result.selected_pages))),
    )

    return Titled(
        "llms.txt Preview",
        Div(
            H1("llms.txt Preview"),
            summary,
            Div(
                Button("Download llms.txt", type="button", onclick=f"window.location='{download_path}'"),
                style="margin: 1rem 0;",
            ),
            H2("Preview"),
            Pre(result.llms_txt_markdown),
            Div(
                Button("Generate another", type="button", onclick="window.location='/'"),
                style="margin-top: 1rem;",
            ),
            style="max-width: 56rem; margin: 2rem auto; padding: 0 1rem;",
        ),
    )
