# Architecture

## Purpose

This document describes the internal architecture of the Automated `llms.txt` Generator and the key design decisions behind it.

The goal of the system is to take a user-provided website URL, crawl the site safely, extract useful metadata, prioritize the most relevant pages, and generate a standards-compliant `llms.txt` file.

This document focuses on **how** the system is structured and **why** the architecture was chosen.

---

## System Overview

At a high level, the system consists of a thin web layer and a set of backend services:

```text
User
  ↓
FastHTML Web App
  ↓
Generation Controller
  ↓
Crawler Service
  ↓
Metadata Extractor
  ↓
Page Prioritizer
  ↓
llms.txt Generator
```

The architecture is intentionally modular so that each component has a single clear responsibility. This makes the code easier to test, maintain, and explain.

---

## Architectural Principles

The system should follow these principles:

- Keep the web layer thin
- Put core logic in services, not routes
- Separate crawling, parsing, ranking, and generation
- Favor deterministic behavior over opaque AI behavior
- Limit complexity unless it directly improves the quality of the generated `llms.txt`
- Make tradeoffs explicit and easy to explain

This project is primarily an extraction and formatting pipeline, not a machine learning system. The architecture reflects that.

---

## Component Breakdown

## 1. FastHTML Web App

The FastHTML app is the user-facing entry point.

Responsibilities:

- Render the homepage
- Accept a website URL
- Trigger generation
- Show generation results
- Provide download of generated `llms.txt`
- Display user-friendly errors

The web layer should not contain business logic beyond request validation and response formatting.

Example route flow:

```text
GET  /           -> render form
POST /generate   -> validate URL, run generation pipeline
GET  /download   -> download generated llms.txt
```

Why FastHTML:

- Keeps the entire project Python-first
- Minimizes frontend complexity
- Makes the UI easy to ship quickly
- Lets engineering effort focus on the crawl/generation pipeline

---

## 2. Generation Controller

This is the orchestration layer between the web app and the backend services.

Responsibilities:

- Normalize and validate the input URL
- Initialize crawl settings
- Invoke the crawler
- Pass crawled content into extraction and prioritization
- Invoke the generator
- Return the final result to the route handler

This component should coordinate services but not implement their internal logic.

Example pipeline:

```text
validate URL
→ crawl pages
→ extract metadata
→ prioritize pages
→ generate llms.txt
→ return markdown
```

---

## 3. Crawler Service

The crawler is responsible for discovering pages within the target website.

Responsibilities:

- Fetch pages
- Extract internal links
- Restrict crawl to the same domain
- Enforce max depth and max page limits
- Avoid revisiting duplicate URLs

Recommended crawl strategy:

- Breadth-first search (BFS)
- Same-domain only
- Ignore obvious non-HTML resources
- Normalize URLs before enqueueing
- Track visited URLs in a set

Why BFS:

- It naturally prioritizes higher-level pages
- It reduces the chance of going too deep into unimportant sections
- It tends to discover navigation pages, documentation roots, and primary content early

Suggested default limits:

- `max_depth = 2` or `3`
- `max_pages = 50` to `100`

Core pseudocode:

```python
queue = [(start_url, 0)]
visited = set()

while queue:
    url, depth = queue.pop(0)
    if url in visited:
        continue
    if depth > max_depth:
        continue

    visited.add(url)
    html = fetch(url)
    links = extract_internal_links(html, url)

    for link in links:
        if link not in visited:
            queue.append((link, depth + 1))
```

---

## 4. Metadata Extractor

The extractor converts raw HTML pages into structured page records.

Responsibilities:

- Parse HTML
- Extract page title
- Extract meta description
- Extract canonical URL if available
- Extract page path
- Optionally derive a fallback summary from visible text

Primary sources:

```html
<title>
<meta name="description">
<link rel="canonical">
```

Fallback behavior:

- If title is missing, derive one from the URL path
- If description is missing, generate a short summary from page text
- If canonical URL is missing, use the fetched URL
- If content is malformed, extract whatever minimal metadata is safely available

The extractor should be resilient to incomplete or messy HTML.

---

## 5. Page Prioritizer

The prioritizer decides which pages should appear in the final `llms.txt`.

Not every crawled page is equally useful. Many websites contain:

- duplicate content
- login pages
- paginated views
- low-value utility pages
- legal or account pages

Responsibilities:

- Score pages
- Remove low-value pages
- Group pages into useful categories if possible
- Keep the final output concise

Possible scoring signals:

- Homepage boost
- Shallow path depth
- Presence in navigation
- URL keywords such as `/docs`, `/guide`, `/api`, `/blog`, `/pricing`, `/about`
- High-quality title and description
- Canonical, stable-looking URLs
- Non-duplicate descriptions or paths

Possible penalties:

- Query-heavy URLs
- Login or auth paths
- Tag/filter/archive pages
- Empty titles/descriptions
- Deep, noisy paths

Recommended output size:

- 20 to 50 pages, depending on site size

This service is a strong place to demonstrate engineering judgment, because the quality of the final `llms.txt` depends heavily on page selection.

---

## 6. llms.txt Generator

The generator turns prioritized pages into the final Markdown file.

Responsibilities:

- Produce a site title
- Produce a short site summary
- Group pages into sections
- Format the output according to the `llms.txt` spec
- Return the final Markdown string

Expected formatting style:

```text
# Site Name
> Short site summary

## Documentation
- [Getting Started](https://example.com/docs/start): Introduction to the platform
- [API Reference](https://example.com/docs/api): Complete API documentation
```

Formatting rules:

- One top-level title
- Optional blockquote summary
- Clear section headings
- Bullet lists of page links
- Each bullet should include title, URL, and description where available

The generator should be deterministic so that the same site produces similar output across runs.

---

## Data Model

A simple internal data model should be used across services.

### Page

```python
from dataclasses import dataclass

@dataclass
class Page:
    url: str
    title: str
    description: str
    path: str
    depth: int
    canonical_url: str | None = None
    score: float = 0.0
    category: str | None = None
```

Why a shared `Page` model:

- Reduces ambiguity between services
- Makes testing easier
- Prevents passing around raw dictionaries everywhere
- Makes the pipeline easier to reason about

---

## Request Lifecycle

The expected lifecycle for a user request is:

```text
1. User submits URL
2. Route validates input
3. Generation controller starts pipeline
4. Crawler discovers pages
5. Extractor produces structured Page objects
6. Prioritizer filters and scores pages
7. Generator builds llms.txt Markdown
8. UI renders preview and offers download
```

This flow should be easy to trace in logs and easy to test end-to-end.

---

## Suggested Repository Layout

```text
llms-txt-generator/
├── app/
│   ├── main.py
│   ├── routes.py
│   └── views.py
├── services/
│   ├── crawler.py
│   ├── extractor.py
│   ├── prioritizer.py
│   ├── generator.py
│   └── pipeline.py
├── models/
│   └── page.py
├── utils/
│   ├── url_utils.py
│   ├── html_utils.py
│   └── robots.py
├── docs/
│   ├── project_spec.md
│   └── architecture.md
├── tests/
│   ├── test_crawler.py
│   ├── test_extractor.py
│   ├── test_prioritizer.py
│   └── test_generator.py
└── README.md
```

Notes:

- `pipeline.py` can contain the orchestration logic
- `views.py` can hold reusable UI fragments if needed
- `robots.py` can encapsulate robots.txt checks if implemented

---

## Error Handling Strategy

The system should fail gracefully.

Possible failures:

- Invalid URL
- DNS failure
- Timeout
- Non-HTML response
- Blocked request
- Malformed HTML
- Empty crawl result

Expected behavior:

- Return clear user-facing error messages
- Log the technical details internally
- Continue partial processing where reasonable
- Avoid crashing the entire app because one page failed

Examples:

- If a single page times out, continue with the rest
- If the homepage cannot be fetched, fail the request clearly
- If metadata is missing, use fallback logic instead of discarding the page immediately

---

## Performance Strategy

The project does not need distributed infrastructure, but it should still be reasonably efficient.

Recommended choices:

- Use `httpx.AsyncClient` for non-blocking HTTP requests
- Limit concurrency to avoid overloading target sites
- Reuse HTTP connections
- Stop crawling once max page count is reached
- Avoid expensive full-page NLP unless truly necessary

Example concurrency approach:

- A bounded async queue
- Configurable max concurrent fetches, e.g. 5 to 10

Why this matters:

- Faster turnaround for the user
- Better crawl throughput
- Lower chance of accidental abuse

---

## Safety and Crawl Hygiene

The crawler should behave responsibly.

Recommended safeguards:

- Restrict to same domain
- Respect `robots.txt` if implemented
- Use request timeouts
- Use a custom user agent
- Skip binary and obviously non-HTML resources
- Avoid infinite loops from repeated paths or URL variants
- Normalize URLs by removing fragments and standardizing slashes

Possible skipped file types:

- PDFs
- images
- videos
- archives
- CSS/JS assets

The goal is not to be a perfect crawler, but to be a safe and practical one.

---

## Tradeoffs and Design Decisions

## Why a modular service architecture?

Because the assignment explicitly values maintainability and code quality. A modular design makes the system easier to test and explain.

## Why not put everything in one route handler?

Because doing so creates a hard-to-maintain blob and hides the key engineering work. Routes should stay thin.

## Why deterministic extraction instead of LLM summarization everywhere?

Because the goal is to generate a reliable, explainable `llms.txt`, not to maximize model usage. Deterministic logic is cheaper, easier to debug, and easier to defend in a presentation.

## Why BFS instead of DFS?

BFS is more likely to find important top-level pages early and less likely to waste crawl budget deep in one irrelevant section.

## Why keep the UI simple?

Because the core engineering challenge is backend crawling and generation, not frontend interaction. A simple UI keeps the project focused.

---

## Testing Strategy

At minimum, the system should include tests for:

### Unit tests

- URL normalization
- internal link extraction
- metadata extraction
- page scoring
- markdown generation

### Integration tests

- crawl a small known website fixture
- verify final `llms.txt` contains expected pages
- verify duplicate URLs are not revisited

### Edge case tests

- missing description
- malformed HTML
- relative links
- trailing slash normalization
- unreachable page during crawl

Testing matters because this project has many small edge cases that are easy to miss without automated coverage.

---

## Observability and Debugging

Even for a small project, basic observability helps.

Useful logs:

- input URL
- normalized root domain
- pages fetched
- pages skipped
- extraction failures
- prioritization decisions
- generation completion

Example logging points:

```text
Starting crawl for https://example.com
Fetched /docs successfully
Skipped /login due to low priority
Generated llms.txt with 24 pages
```

These logs make demos and debugging much easier.

---

## Future Extensions

The architecture should leave room for later improvements without requiring a rewrite.

Possible future features:

- Sitemap parsing before crawl
- Optional JavaScript rendering for dynamic sites
- Background job execution for slow crawls
- Persisted crawl history
- Multiple output modes such as `llms-full.txt`
- Admin/debug page showing crawl decisions
- Heuristic or model-based categorization improvements

Because the services are separated, these can be added incrementally.

---

## Summary

This architecture is intentionally simple, modular, and backend-first.

The project should present as:

- easy to understand
- easy to explain
- safe to run
- cleanly organized
- strong on engineering fundamentals

The most important qualities are not flashy infrastructure or UI polish, but good crawl hygiene, sensible page selection, spec-compliant output, and maintainable code structure.
