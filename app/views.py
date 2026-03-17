"""Reusable view helpers and UI fragments."""

from __future__ import annotations

from fasthtml.common import Button, Div, Form, H1, H2, Input, Li, P, Pre, Script, Strong, Titled, Ul

from services.pipeline import GenerationResult


def render_home_page(
    *,
    url_value: str = "",
    error_message: str | None = None,
    force_generate: bool = False,
    respect_robots_txt: bool = True,
):
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
                checked=force_generate,
            ),
            "Force generate even if llms.txt exists",
            style="margin-top: 1rem;",
        ),
        Div(
            Input(
                type="checkbox",
                name="respect_robots_txt",
                value="1",
                id="respect_robots_txt",
                checked=respect_robots_txt,
            ),
            "Respect robots.txt",
            style="margin-top: 0.75rem;",
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


def render_progress_page(
    *,
    normalized_url: str,
    progress_path: str,
) :
    """Render a polling progress page while generation runs in the background."""

    script = Script(
        f"""
const progressPath = {progress_path!r};
const statusMessage = document.getElementById("status-message");
const depthValue = document.getElementById("depth-value");
const visitedValue = document.getElementById("visited-value");
const queuedValue = document.getElementById("queued-value");
const errorMessage = document.getElementById("error-message");
const homeAction = document.getElementById("home-action");

async function pollProgress() {{
  try {{
    const response = await fetch(progressPath, {{ cache: "no-store" }});
    if (!response.ok) {{
      throw new Error("Unable to load progress");
    }}

    const progress = await response.json();
    statusMessage.textContent = progress.message;
    depthValue.textContent = String(progress.depth);
    visitedValue.textContent = String(progress.pages_visited);
    queuedValue.textContent = String(progress.pages_queued);

    if (progress.status === "completed" && progress.result_path) {{
      window.location = progress.result_path;
      return;
    }}

    if (progress.status === "failed") {{
      errorMessage.textContent = progress.error_message || "Something went wrong while generating llms.txt.";
      errorMessage.style.display = "block";
      homeAction.style.display = "inline-block";
      return;
    }}
  }} catch (error) {{
    errorMessage.textContent = "We lost the progress update connection. Please try again.";
    errorMessage.style.display = "block";
    homeAction.style.display = "inline-block";
    return;
  }}

  window.setTimeout(pollProgress, 500);
}}

window.addEventListener("load", () => {{
  window.setTimeout(pollProgress, 100);
}});
"""
    )

    return Titled(
        "Generating llms.txt",
        Div(
            H1("Generating llms.txt"),
            P(
                f"Crawling {normalized_url}",
                id="status-message",
                style="font-weight: 600;",
            ),
            Ul(
                Li(Strong("Depth: "), Strong("0", id="depth-value")),
                Li(Strong("Pages visited: "), Strong("0", id="visited-value")),
                Li(Strong("Pages queued: "), Strong("0", id="queued-value")),
            ),
            P("This page updates automatically while the crawler runs."),
            Div(
                id="error-message",
                style="display: none; color: #b02a37; margin-top: 1rem;",
            ),
            Div(
                Button("Back home", type="button", onclick="window.location='/'"),
                id="home-action",
                style="display: none; margin-top: 1rem;",
            ),
            script,
            style="max-width: 48rem; margin: 2rem auto; padding: 0 1rem;",
        ),
    )
