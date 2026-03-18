"""Result-page view helpers."""

from __future__ import annotations

from fasthtml.common import Button, Div, H2, Li, P, Pre, Script, Strong, Ul

from services.pipeline import GenerationResult

from .shared import render_card, render_intro_block, render_page_shell


def render_result_page(result: GenerationResult, *, download_path: str):
    """Render the result page with crawl summary and llms.txt preview."""

    return render_page_shell(
        "Automated llms.txt Generator",
        render_intro_block(
            "Generation Summary",
            "Review the crawl outcome, inspect the selected pages, and copy or download the generated llms.txt in one place.",
        ),
        render_card(
            _render_result_summary(result),
            *_render_crawl_summary_block(result),
            _render_result_actions(download_path),
        ),
        render_card(
            H2("Generated llms.txt"),
            Pre(result.llms_txt_markdown, id="llms-txt-preview"),
        ),
        _render_copy_script(),
        max_width="56rem",
    )


def _render_result_summary(result: GenerationResult) -> Ul:
    return Ul(
        Li(Strong("Normalized URL: "), result.normalized_root_url),
        Li(
            Strong("Source: "),
            "Existing llms.txt" if result.used_existing_llms_txt else "Generated from website crawl",
        ),
        Li(Strong("Crawled pages: "), str(len(result.crawled_pages))),
        Li(Strong("Selected pages: "), str(len(result.selected_pages))),
        cls="summary-list",
    )


def _render_crawl_summary_block(result: GenerationResult) -> tuple[H2, Ul] | tuple[()]:
    if result.crawl_summary is None:
        return ()

    return (
        H2("Crawl Summary", cls="section-heading"),
        Ul(
            Li(Strong("Pages crawled: "), str(result.crawl_summary.pages_crawled)),
            Li(Strong("Depth reached: "), str(result.crawl_summary.depth_reached)),
            Li(
                Strong("Total crawl time: "),
                f"{result.crawl_summary.crawl_time_seconds:.2f} seconds",
            ),
            cls="summary-list",
        ),
    )


def _render_result_actions(download_path: str) -> Div:
    return Div(
        Button("Copy llms.txt", type="button", onclick="copyLlmsTxt()", cls="button button-secondary"),
        Button(
            "Download llms.txt",
            type="button",
            onclick=f"window.location='{download_path}'",
            cls="button button-primary",
        ),
        Button("Generate another", type="button", onclick="window.location='/'", cls="button button-secondary"),
        P("", id="copy-status", cls="copy-status"),
        cls="action-row",
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
