# Automated llms.txt Generator

[![Python application](https://github.com/tiger9800/llms.txt-generator/actions/workflows/python-app.yml/badge.svg)](https://github.com/tiger9800/llms.txt-generator/actions/workflows/python-app.yml)

Generate a standards-aligned `llms.txt` file for a public website by crawling, extracting, prioritizing, and formatting the most useful pages into a concise Markdown output.

## Live demo

- Deployment: https://llmstxt-generator-production-571b.up.railway.app/

## Features

- FastHTML web app with a form, live crawl progress, crawl summary, result preview, copy action, and one-click download.
- End-to-end generation pipeline: detect existing `llms.txt` -> crawl -> extract metadata -> prioritize pages -> generate Markdown.
- Existing `llms.txt` detection for both site-root and subpath targets, with an option to force generation instead.
- Crawl safety controls including same-domain restriction, HTML-only link filtering, configurable crawl limits, optional `robots.txt` enforcement, and optional sitemap seeding.
- Layered concurrent BFS crawling with deterministic output ordering.
- Metadata extraction for titles, descriptions, canonical URLs, and fallback summaries from page content.
- Deterministic page scoring that boosts likely high-value pages and penalizes low-value or noisy URLs.
- Conditional `## Optional` output support for lower-priority selected pages, keeping the main sections tighter without dropping useful links.
- Evaluation harness for comparing generated output against existing `llms.txt` files using URL, slug, and title overlap metrics.

Implemented features are described here; planned work is tracked separately in [docs/improvement_plan.md](docs/improvement_plan.md).

## How it works

1. Submit a public `http(s)` URL in the web app.
2. The pipeline normalizes the URL and checks whether the target already exposes an `llms.txt`.
3. If generation is needed, the crawler performs a same-domain breadth-first crawl with depth, page-count, timeout, concurrency, `robots.txt`, and optional sitemap settings.
4. Extracted pages are converted into typed `Page` records with titles, descriptions, paths, and canonical URLs.
5. The prioritizer deduplicates near-duplicates and scores pages using deterministic URL and metadata heuristics.
6. The generator groups selected pages into sections, moves a small lower-priority tail into `## Optional` when helpful, and renders the final Markdown preview and downloadable `llms.txt`.

## Architecture

The system is split into a thin FastHTML web layer and a deterministic backend pipeline. The UI handles input, progress, and result rendering, while focused service modules handle discovery, extraction, prioritization, and Markdown generation.

```text
User
  ->
FastHTML Web App
  ->
Generation Pipeline
  ->
Components
  -> Existing llms.txt Detector
  -> robots.txt Checker
  -> Concurrent BFS Crawler
  ->
Metadata Extractor
  ->
Page Prioritizer
  ->
llms.txt Generator
  ->
UI Output
```

### Main components

- Web app (FastHTML UI): accepts input, shows progress, renders results, and handles download/copy actions.
- Generation pipeline: orchestrates the full request from URL normalization through final Markdown output.
- Existing `llms.txt` detector: checks for an existing file at the root or subpath before crawling.
- `robots.txt` checker: loads policy once per crawl and optionally enforces allow/deny rules.
- Concurrent BFS crawler: performs a layered same-domain crawl with bounded concurrency and crawl limits.
- Metadata extractor: parses HTML into typed page records with title, description, path, and canonical URL fields.
- Page prioritizer: deduplicates pages and ranks them with deterministic heuristics.
- `llms.txt` generator: groups selected pages into sections, optionally adds a final `## Optional` section for lower-priority selected pages, and renders the final Markdown file.

### Request Flow

1. The user submits a website URL in the FastHTML app.
2. The pipeline normalizes the URL and checks for an existing `llms.txt`.
3. If needed, the crawler fetches pages with concurrent BFS while respecting configured crawl controls.
4. The extractor converts crawled HTML into structured page metadata.
5. The prioritizer scores and selects the most useful pages.
6. The generator renders the final `llms.txt`, and the UI shows a preview plus copy/download actions.

### Repository Structure

```text
app/        # FastHTML UI, routes, and page rendering
services/   # core crawling, extraction, prioritization, and generation logic
models/     # shared data structures
utils/      # reusable helpers
tests/      # automated tests and evaluation harness
```

## Deployment

The application is a lightweight Python web service with no required
environment variables. It can be deployed on any platform that supports
running a Python process.

### Railway (Current Deployment)

This project is currently deployed on Railway, which provides a simple
and fast way to deploy Python applications with minimal configuration.

**Build command:** `pip install -r requirements.txt`

**Start command:** `python -m app.main`

### Why Railway?

Railway was chosen for this project because:

- Zero-config deployment
- Fast iteration and redeploys
- Good defaults for networking and process management
- Ideal for demos and rapid prototyping

---

## Deploy It Yourself

You can deploy your own instance of this app with one click:

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Notes

After clicking, connect your GitHub repo and use:

Build command: `pip install -r requirements.txt`  
Start command: `python -m app.main`

---

## Alternative Deployment Options

### Fly.io

- Global deployment
- Requires Docker

### Render

- Simple setup
- Free tier available

### Docker + Cloud (AWS / GCP / Azure)

- Full control and scalability
- More setup required

---

## Local development

This project is developed and tested with **Python 3.10**. The
repository includes a [`.python-version`](.python-version) file pinned
to `3.10.11` for local tooling such as `pyenv`.

### 1. Create a virtual environment

```bash
python3.10 -m venv venv
source venv/bin/activate  # macOS / Linux
venv\Scripts\activate     # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
python -m app.main
```

### 4. Open in browser

```text
http://localhost:5001
```

---

## Summary

Railway was selected to optimize for:

- speed of development
- simplicity of deployment
- ease of demonstration

The architecture remains platform-agnostic and can be migrated to other
providers as needed.

## Testing

Run the automated test suite:

```bash
pytest
```

Run the evaluation harness against the checked-in site list in [tests/evaluation/sites.txt](tests/evaluation/sites.txt):

```bash
python -m tests.evaluation.run_eval
```

Optional evaluation flags:

- `--show-markdown`
- `--show-all-diffs`
