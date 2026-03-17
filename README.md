# Automated llms.txt Generator

[![Python application](https://github.com/tiger9800/llms.txt-generator/actions/workflows/python-app.yml/badge.svg)](https://github.com/tiger9800/llms.txt-generator/actions/workflows/python-app.yml)

Generate a standards-aligned `llms.txt` file for a public website by crawling, extracting, prioritizing, and formatting the most useful pages into a concise Markdown output.

## Live demo

- Deployment: https://llmstxt-generator-production-571b.up.railway.app/

## Features

- FastHTML web app with a simple form, result preview, and one-click download.
- End-to-end generation pipeline: crawl -> extract metadata -> prioritize pages -> generate `llms.txt`.
- Existing `llms.txt` detection for both site-root and subpath targets, with an option to force generation instead.
- Crawl safety controls including same-domain restriction, HTML-only link filtering, configurable crawl limits, and optional `robots.txt` enforcement.
- Layered concurrent BFS crawling with deterministic output ordering.
- Metadata extraction for titles, descriptions, canonical URLs, and fallback summaries from page content.
- Deterministic page scoring that boosts likely high-value pages and penalizes low-value or noisy URLs.
- Evaluation harness for comparing generated output against existing `llms.txt` files using URL, slug, and title overlap metrics.

Planned work is tracked separately in [docs/improvement_plan.md](/Users/davydfridman/Desktop/Code%20References/LLM_Txt_Generator/docs/improvement_plan.md). Notable items that are documented but not implemented yet include anti-bot/interstitial detection, user-facing crawl configuration, and sitemap support.

## How it works

1. Submit a public `http(s)` URL in the web app.
2. The pipeline normalizes the URL and checks whether the target already exposes an `llms.txt`.
3. If generation is needed, the crawler performs a same-domain breadth-first crawl with depth, page-count, timeout, and concurrency limits.
4. Extracted pages are converted into typed `Page` records with titles, descriptions, paths, and canonical URLs.
5. The prioritizer deduplicates near-duplicates and scores pages using deterministic URL and metadata heuristics.
6. The generator groups selected pages into sections and renders the final Markdown preview and downloadable `llms.txt`.

## Architecture

- `app/`: thin FastHTML web layer for form handling, preview rendering, and downloads.
- `services/crawler.py`: concurrent BFS crawler with same-domain filtering, crawl limits, timing logs, and optional `robots.txt` enforcement.
- `services/extractor.py`: HTML metadata extraction and fallback summary generation.
- `services/prioritizer.py`: deterministic page scoring, deduplication, and category assignment.
- `services/generator.py`: deterministic `llms.txt` Markdown generation.
- `services/pipeline.py`: orchestration layer that keeps route handlers free of crawl and generation logic.
- `models/page.py`: shared typed page model used across the pipeline.
- `tests/`: unit tests plus an evaluation harness for comparing generated output against real `llms.txt` files.

## Local development

Install dependencies and run the app from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Then open `http://localhost:5001`.

## Deployment

The current hosted app is available at:

- https://llmstxt-generator-production-571b.up.railway.app/

The repository does not currently include deployment configuration files such as a `Dockerfile`, `railway.json`, or `Procfile`, so deployment-specific setup is external to the repo at the moment.

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
