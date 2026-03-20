"""Shared styling and layout helpers for page renderers."""

from __future__ import annotations

from fasthtml.common import Div, H1, P, Style, Titled


def render_page_shell(title: str, *children, max_width: str):
    return Titled(
        title,
        Style(base_styles()),
        Div(
            *children,
            cls="page-shell",
            style=f"--page-max-width: {max_width};",
        ),
    )


def render_intro_block(title: str, description: str) -> Div:
    return Div(
        P("Deterministic website-to-llms.txt pipeline", cls="eyebrow"),
        H1(title),
        P(description, cls="lead"),
        cls="hero-block",
    )


def render_card(*children) -> Div:
    return Div(*children, cls="card")


def base_styles() -> str:
    return """
:root {
  --bg: #f5f1e8;
  --surface: rgba(255, 252, 247, 0.82);
  --border: rgba(36, 54, 74, 0.14);
  --text: #17212b;
  --muted: #526171;
  --accent: #0f5c78;
  --accent-strong: #0b4357;
  --shadow: 0 24px 60px rgba(23, 33, 43, 0.08);
  --radius: 24px;
}

* { box-sizing: border-box; }

html {
  min-height: 100%;
  background:
    radial-gradient(circle at top left, rgba(15, 92, 120, 0.12), transparent 32rem),
    linear-gradient(180deg, var(--bg) 0%, #f8f5ee 48%, #f3efe7 100%);
}

body {
  margin: 0;
  min-height: 100vh;
  color: var(--text);
  background:
    radial-gradient(circle at top left, rgba(15, 92, 120, 0.12), transparent 32rem),
    linear-gradient(180deg, var(--bg) 0%, #f8f5ee 48%, #f3efe7 100%);
  font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
}

h1, h2, strong, summary {
  color: #10202f;
}

h1 {
  margin: 0;
  font-size: clamp(2.2rem, 4vw, 3.5rem);
  line-height: 1.02;
  letter-spacing: -0.04em;
}

h2 {
  margin: 0 0 1rem;
  font-size: 1.15rem;
  letter-spacing: -0.02em;
}

p, li {
  line-height: 1.6;
}

.page-shell {
  max-width: var(--page-max-width);
  margin: 0 auto;
  min-height: 100vh;
  padding: 2.5rem 1rem 4rem;
}

.hero-block {
  padding: 0.5rem 0 1.5rem;
}

.eyebrow {
  margin: 0 0 0.85rem;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 0.78rem;
  font-weight: 700;
}

.lead {
  max-width: 46rem;
  margin: 0.9rem 0 0;
  color: var(--muted);
  font-size: 1.05rem;
}

.card {
  margin-top: 1.25rem;
  padding: 1.4rem 1.4rem 1.5rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  backdrop-filter: blur(10px);
}

.home-form,
.summary-list {
  display: grid;
  gap: 0.9rem;
}

.form-intro,
.advanced-copy,
.progress-copy {
  margin: 0;
  color: var(--muted);
}

.url-input,
.number-input {
  width: 100%;
  border: 1px solid rgba(36, 54, 74, 0.18);
  border-radius: 16px;
  padding: 0.9rem 1rem;
  background: rgba(255, 255, 255, 0.88);
  color: var(--text);
  font: inherit;
}

.checkbox-row {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  margin-top: 0.15rem;
}

.checkbox-input {
  margin-top: 0.28rem;
  accent-color: var(--accent);
}

.checkbox-label {
  margin: 0;
}

.advanced-panel {
  margin-top: 1rem;
  padding: 0.9rem 1rem 1rem;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: rgba(230, 237, 244, 0.36);
}

.advanced-summary {
  cursor: pointer;
}

.number-field {
  margin-top: 0.85rem;
}

.field-label {
  display: block;
  margin-bottom: 0.45rem;
}

.field-help {
  margin: 0.35rem 0 0;
  color: var(--muted);
  font-size: 0.92rem;
}

.form-actions {
  margin-top: 1rem;
}

.button {
  border: 0;
  border-radius: 999px;
  padding: 0.8rem 1.15rem;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.button-primary {
  background: var(--accent);
  color: #f7fbff;
}

.button-secondary {
  background: rgba(255, 255, 255, 0.82);
  color: var(--text);
  border: 1px solid rgba(36, 54, 74, 0.14);
}

.action-row {
  margin: 1.1rem 0 0;
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.copy-status {
  margin: 0;
  color: var(--muted);
}

.section-heading {
  margin-top: 1.25rem;
}

.summary-list {
  padding-left: 1.2rem;
}

#llms-txt-preview {
  margin: 0;
  padding: 1.1rem 1.15rem;
  border-radius: 18px;
  border: 1px solid rgba(36, 54, 74, 0.1);
  background: #fcfaf6;
  overflow-x: auto;
  line-height: 1.65;
  font-size: 0.95rem;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.loading-indicator {
  width: 1rem;
  height: 1rem;
  border: 2px solid #cbd5e1;
  border-top-color: var(--accent);
  border-radius: 999px;
  animation: spin 0.8s linear infinite;
}

.status-message {
  margin: 0;
  font-weight: 700;
}

.progress-error {
  display: none;
  margin-top: 1rem;
  color: #9b1c1c;
}

.home-action {
  display: none;
  margin-top: 1rem;
}

.error-banner {
  margin: 0 0 1rem;
  padding: 1rem 1rem 0.9rem;
  border: 1px solid rgba(185, 63, 63, 0.35);
  border-radius: 18px;
  background: rgba(255, 243, 241, 0.92);
}

@media (max-width: 640px) {
  .page-shell {
    padding-top: 1.5rem;
  }

  .card {
    padding: 1.1rem;
    border-radius: 20px;
  }

  .action-row {
    align-items: stretch;
  }

  .action-row .button {
    width: 100%;
  }
}
"""
