"""Progress-page view helpers."""

from __future__ import annotations

from fasthtml.common import Button, Div, Li, P, Script, Strong, Ul

from .shared import render_card, render_intro_block, render_page_shell


def render_progress_page(
    *,
    normalized_url: str,
    progress_path: str,
):
    """Render a polling progress page while generation runs in the background."""

    return render_page_shell(
        "Automated llms.txt Generator",
        render_intro_block(
            "Generating llms.txt",
            "We are crawling the site, collecting the most useful pages, and assembling a clean llms.txt preview for review.",
        ),
        render_card(
            Div(
                Div(
                    aria_label="Loading",
                    id="loading-indicator",
                    role="status",
                    cls="loading-indicator",
                ),
                Strong("Crawling and generating llms.txt...", id="loading-label"),
                id="loading-state",
                cls="loading-state",
            ),
            P(
                f"Crawling {normalized_url}",
                id="status-message",
                cls="status-message",
            ),
            Ul(
                Li(Strong("Depth: "), Strong("0", id="depth-value")),
                Li(Strong("Pages visited: "), Strong("0", id="visited-value")),
                Li(Strong("Pages queued: "), Strong("0", id="queued-value")),
                cls="summary-list",
            ),
            P("This page updates automatically while generation is in progress.", cls="progress-copy"),
            Script(
                """
const loadingStyle = document.createElement("style");
loadingStyle.textContent = "@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }";
document.head.appendChild(loadingStyle);
"""
            ),
            Div(
                id="error-message",
                cls="progress-error",
            ),
            Div(
                Button("Back home", type="button", onclick="window.location='/'", cls="button button-secondary"),
                id="home-action",
                cls="home-action",
            ),
        ),
        _render_progress_script(progress_path),
        max_width="48rem",
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

    window.setTimeout(pollProgress, 750);
  }} catch (error) {{
    setLoadingState(false);
    errorMessage.textContent = "Unable to refresh progress. Please try again.";
    errorMessage.style.display = "block";
    homeAction.style.display = "inline-block";
  }}
}}

window.addEventListener("load", () => {{
  window.setTimeout(pollProgress, 100);
}});
"""
    )
