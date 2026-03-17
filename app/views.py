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

    return Titled(
        "Automated llms.txt Generator",
        Div(
            H1("Automated llms.txt Generator"),
            *_render_home_error_block(error_message),
            _render_home_form(
                url_value=url_value,
                force_generate=force_generate,
                respect_robots_txt=respect_robots_txt,
            ),
            style="max-width: 48rem; margin: 2rem auto; padding: 0 1rem;",
        ),
    )


def render_result_page(result: GenerationResult, *, download_path: str):
    """Render the result page with crawl summary and llms.txt preview."""

    return Titled(
        "llms.txt Preview",
        Div(
            H1("llms.txt Preview"),
            _render_result_summary(result),
            *_render_crawl_summary_block(result),
            _render_result_actions(download_path),
            H2("Preview"),
            Pre(result.llms_txt_markdown, id="llms-txt-preview"),
            Div(
                Button("Generate another", type="button", onclick="window.location='/'"),
                style="margin-top: 1rem;",
            ),
            _render_copy_script(),
            style="max-width: 56rem; margin: 2rem auto; padding: 0 1rem;",
        ),
    )


def _render_home_form(
    *,
    url_value: str,
    force_generate: bool,
    respect_robots_txt: bool,
) -> Form:
    return Form(
        P("Enter a public website URL to generate a preview of its llms.txt file."),
        Input(
            type="url",
            name="url",
            value=url_value,
            placeholder="https://example.com",
            required=True,
        ),
        _render_checkbox(
            name="force_generate",
            label="Force generate even if llms.txt exists",
            checked=force_generate,
            margin_top="1rem",
        ),
        _render_checkbox(
            name="respect_robots_txt",
            label="Respect robots.txt",
            checked=respect_robots_txt,
            margin_top="0.75rem",
        ),
        Div(Button("Generate llms.txt", type="submit"), style="margin-top: 1rem;"),
        action="/generate",
        method="post",
    )


def _render_checkbox(
    *,
    name: str,
    label: str,
    checked: bool,
    margin_top: str,
) -> Div:
    return Div(
        Input(
            type="checkbox",
            name=name,
            value="1",
            id=name,
            checked=checked,
        ),
        label,
        style=f"margin-top: {margin_top};",
    )


def _render_home_error_block(error_message: str | None) -> tuple[Div, ...]:
    if not error_message:
        return ()

    return (
        Div(
            Strong("We couldn't generate an llms.txt file."),
            P(error_message),
            style="padding: 1rem; border: 1px solid #d9534f; margin: 1rem 0;",
        ),
    )


def _render_result_summary(result: GenerationResult) -> Ul:
    return Ul(
        Li(Strong("Normalized URL: "), result.normalized_root_url),
        Li(
            Strong("Source: "),
            "Existing llms.txt" if result.used_existing_llms_txt else "Generated from crawl",
        ),
        Li(Strong("Crawled pages: "), str(len(result.crawled_pages))),
        Li(Strong("Selected pages: "), str(len(result.selected_pages))),
    )


def _render_crawl_summary_block(result: GenerationResult) -> tuple[H2, Ul] | tuple[()]:
    if result.crawl_summary is None:
        return ()

    return (
        H2("Crawl Summary"),
        Ul(
            Li(Strong("Pages crawled: "), str(result.crawl_summary.pages_crawled)),
            Li(Strong("Depth reached: "), str(result.crawl_summary.depth_reached)),
            Li(
                Strong("Total crawl time: "),
                f"{result.crawl_summary.crawl_time_seconds:.2f} seconds",
            ),
        ),
    )


def _render_result_actions(download_path: str) -> Div:
    return Div(
        Button("Copy llms.txt", type="button", onclick="copyLlmsTxt()"),
        Button("Download llms.txt", type="button", onclick=f"window.location='{download_path}'"),
        P("", id="copy-status", style="display: inline-block; margin-left: 1rem;"),
        style="margin: 1rem 0; display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap;",
    )


def render_progress_page(
    *,
    normalized_url: str,
    progress_path: str,
) :
    """Render a polling progress page while generation runs in the background."""

    return Titled(
        "Generating llms.txt",
        Div(
            H1("Generating llms.txt"),
            Div(
                Div(
                    aria_label="Loading",
                    id="loading-indicator",
                    role="status",
                    style=(
                        "width: 1rem; height: 1rem; border: 2px solid #cbd5e1; "
                        "border-top-color: #0f172a; border-radius: 999px; "
                        "animation: spin 0.8s linear infinite;"
                    ),
                ),
                Strong("Working...", id="loading-label"),
                id="loading-state",
                style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;",
            ),
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
            P("This page updates automatically while generation is in progress."),
            Script(
                """
const loadingStyle = document.createElement("style");
loadingStyle.textContent = "@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }";
document.head.appendChild(loadingStyle);
"""
            ),
            Div(
                id="error-message",
                style="display: none; color: #b02a37; margin-top: 1rem;",
            ),
            Div(
                Button("Back home", type="button", onclick="window.location='/'"),
                id="home-action",
                style="display: none; margin-top: 1rem;",
            ),
            _render_progress_script(progress_path),
            style="max-width: 48rem; margin: 2rem auto; padding: 0 1rem;",
        ),
    )


def _render_copy_script() -> Script:
    """Return the inline script used by the result-page copy button."""

    return Script(
        """
function fallbackCopyText(text) {
  const copyBuffer = document.createElement("textarea");
  copyBuffer.value = text;
  copyBuffer.setAttribute("readonly", "");
  copyBuffer.style.position = "absolute";
  copyBuffer.style.left = "-9999px";
  document.body.appendChild(copyBuffer);
  copyBuffer.select();
  copyBuffer.setSelectionRange(0, copyBuffer.value.length);

  try {
    return document.execCommand("copy");
  } finally {
    document.body.removeChild(copyBuffer);
  }
}

async function copyLlmsTxt() {
  const preview = document.getElementById("llms-txt-preview");
  const copyStatus = document.getElementById("copy-status");
  if (preview === null || copyStatus === null) {
    return;
  }

  const previewText = preview.textContent || "";

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(previewText);
      copyStatus.textContent = "Copied.";
      return;
    }

    if (fallbackCopyText(previewText)) {
      copyStatus.textContent = "Copied.";
      return;
    }

    copyStatus.textContent = "Copy failed.";
  } catch (error) {
    if (fallbackCopyText(previewText)) {
      copyStatus.textContent = "Copied.";
      return;
    }

    copyStatus.textContent = "Copy failed.";
  }

  if (!navigator.clipboard && !window.isSecureContext) {
    copyStatus.textContent = "Copy failed.";
  }
}
"""
    )


def _render_progress_script(progress_path: str) -> Script:
    """Return the inline script used by the progress page."""

    return Script(
        f"""
const progressPath = {progress_path!r};
const statusMessage = document.getElementById("status-message");
const depthValue = document.getElementById("depth-value");
const visitedValue = document.getElementById("visited-value");
const queuedValue = document.getElementById("queued-value");
const errorMessage = document.getElementById("error-message");
const homeAction = document.getElementById("home-action");
const loadingState = document.getElementById("loading-state");
const loadingLabel = document.getElementById("loading-label");

function setLoadingState(isRunning) {{
  if (loadingState === null) {{
    return;
  }}

  loadingState.style.display = isRunning ? "flex" : "none";
  if (!isRunning && loadingLabel !== null) {{
    loadingLabel.textContent = "";
  }}
}}

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
      setLoadingState(false);
      window.location = progress.result_path;
      return;
    }}

    if (progress.status === "failed") {{
      setLoadingState(false);
      errorMessage.textContent = progress.error_message || "Something went wrong while generating llms.txt.";
      errorMessage.style.display = "block";
      homeAction.style.display = "inline-block";
      return;
    }}
  }} catch (error) {{
    setLoadingState(false);
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
