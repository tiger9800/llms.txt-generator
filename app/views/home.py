"""Home-page view helpers."""

from __future__ import annotations

from fasthtml.common import Button, Details, Div, Form, Input, P, Strong, Summary

from services.crawler import (
    CrawlerConfig,
    MAX_MAX_DEPTH,
    MAX_MAX_PAGES,
    MAX_TIMEOUT,
    MIN_MAX_DEPTH,
    MIN_MAX_PAGES,
    MIN_TIMEOUT,
)

from .shared import render_card, render_intro_block, render_page_shell


def render_home_page(
    *,
    url_value: str = "",
    error_message: str | None = None,
    force_generate: bool = False,
    respect_robots_txt: bool = True,
    use_sitemap: bool = True,
    crawl_config: CrawlerConfig | None = None,
):
    """Render the home page with the generation form and optional error state."""

    return render_page_shell(
        "Automated llms.txt Generator",
        render_intro_block(
            "Generate an llms.txt file for any website",
            "Deterministically crawl public websites, rank the most useful pages, and generate a polished llms.txt preview before you download it.",
        ),
        render_card(
            *_render_home_error_block(error_message),
            _render_home_form(
                url_value=url_value,
                force_generate=force_generate,
                respect_robots_txt=respect_robots_txt,
                use_sitemap=use_sitemap,
                crawl_config=crawl_config or CrawlerConfig(use_sitemap=use_sitemap),
            ),
        ),
        max_width="48rem",
    )


def _render_home_form(
    *,
    url_value: str,
    force_generate: bool,
    respect_robots_txt: bool,
    use_sitemap: bool,
    crawl_config: CrawlerConfig,
) -> Form:
    return Form(
        P(
            "Enter a public website URL to generate a preview of its llms.txt file.",
            cls="form-intro",
        ),
        Input(
            type="url",
            name="url",
            value=url_value,
            placeholder="https://example.com",
            required=True,
            cls="url-input",
        ),
        _render_checkbox(
            name="force_generate",
            label="Force generate even if llms.txt exists",
            checked=force_generate,
        ),
        _render_checkbox(
            name="respect_robots_txt",
            label="Respect robots.txt",
            checked=respect_robots_txt,
        ),
        _render_checkbox(
            name="use_sitemap",
            label="Use sitemap.xml when available",
            checked=use_sitemap,
        ),
        _render_advanced_crawl_options(crawl_config),
        Div(Button("Generate llms.txt", type="submit", cls="button button-primary"), cls="form-actions"),
        action="/generate",
        method="post",
        cls="home-form",
    )


def _render_checkbox(
    *,
    name: str,
    label: str,
    checked: bool,
) -> Div:
    return Div(
        Input(
            type="checkbox",
            name=name,
            value="1",
            id=name,
            checked=checked,
            cls="checkbox-input",
        ),
        P(label, cls="checkbox-label"),
        cls="checkbox-row",
    )


def _render_advanced_crawl_options(crawl_config: CrawlerConfig) -> Details:
    return Details(
        Summary("Advanced crawl options", cls="advanced-summary"),
        P("These settings let you tune crawl depth, size, and timeout.", cls="advanced-copy"),
        _render_numeric_input(
            name="max_depth",
            label="Max depth",
            value=str(crawl_config.max_depth),
            min_value=str(MIN_MAX_DEPTH),
            max_value=str(MAX_MAX_DEPTH),
            step="1",
            help_text=f"Allowed range: {MIN_MAX_DEPTH} to {MAX_MAX_DEPTH}.",
        ),
        _render_numeric_input(
            name="max_pages",
            label="Max pages",
            value=str(crawl_config.max_pages),
            min_value=str(MIN_MAX_PAGES),
            max_value=str(MAX_MAX_PAGES),
            step="1",
            help_text=f"Allowed range: {MIN_MAX_PAGES} to {MAX_MAX_PAGES}.",
        ),
        _render_numeric_input(
            name="request_timeout",
            label="Request timeout (seconds)",
            value=f"{crawl_config.timeout:.1f}",
            min_value=f"{MIN_TIMEOUT:.1f}",
            max_value=f"{MAX_TIMEOUT:.1f}",
            step="0.5",
            help_text=f"Allowed range: {MIN_TIMEOUT:.1f} to {MAX_TIMEOUT:.1f} seconds.",
        ),
        cls="advanced-panel",
    )


def _render_numeric_input(
    *,
    name: str,
    label: str,
    value: str,
    min_value: str,
    max_value: str,
    step: str,
    help_text: str,
) -> Div:
    return Div(
        Strong(label, cls="field-label"),
        Input(
            type="number",
            name=name,
            value=value,
            min=min_value,
            max=max_value,
            step=step,
            required=True,
            cls="number-input",
        ),
        P(help_text, cls="field-help"),
        cls="number-field",
    )


def _render_home_error_block(error_message: str | None) -> tuple[Div, ...]:
    if not error_message:
        return ()

    return (
        Div(
            Strong("We couldn't generate an llms.txt file."),
            P(error_message),
            cls="error-banner",
        ),
    )
