# Coding Guidelines

## Purpose

This document defines the coding standards and implementation guidelines for the Automated `llms.txt` Generator.

The goals of these guidelines are to keep the codebase:

- readable
- maintainable
- testable
- easy to explain during review
- friendly to both human contributors and coding agents

This project should favor clarity and good engineering judgment over cleverness.

---

## General Principles

Follow these principles throughout the codebase:

- Prefer simple, explicit code over clever abstractions
- Keep functions small and focused
- Keep modules single-purpose
- Make data flow easy to trace
- Favor deterministic logic over opaque behavior
- Write code that is easy to test
- Optimize only when there is a clear need

When choosing between “shorter” and “clearer,” prefer clearer.

---

## Project Priorities

In order of importance, optimize for:

1. Correctness
2. Readability
3. Maintainability
4. Testability
5. Performance
6. Conciseness

This is a take-home project, so code quality and explanation matter more than micro-optimizations.

---

## Language and Style

The project is Python-first.

Style requirements:

- Use Python 3.10+ features where appropriate
- Follow PEP 8
- Use type hints everywhere practical
- Prefer dataclasses or clear typed models for structured data
- Prefer descriptive names over short names
- Avoid unnecessary metaprogramming
- Avoid deeply nested logic where possible

Examples:

Good:

```python
def normalize_url(url: str) -> str:
    ...
```

Bad:

```python
def n(u):
    ...
```

---

## Naming Conventions

Use descriptive, consistent names.

### Files

Use lowercase snake_case filenames:

- `crawler.py`
- `extractor.py`
- `prioritizer.py`
- `generator.py`

### Functions

Use verbs for actions:

- `crawl_site`
- `extract_metadata`
- `score_page`
- `generate_llms_txt`

### Classes

Use PascalCase:

- `Page`
- `CrawlerConfig`
- `GenerationPipeline`

### Variables

Use descriptive snake_case names:

- `normalized_url`
- `visited_urls`
- `max_depth`
- `page_score`

Avoid vague names such as:

- `data`
- `obj`
- `thing`
- `temp`

unless the scope is tiny and the meaning is obvious.

---

## File Organization

Each file should have a clear single purpose.

Recommended structure:

- `app/` for web entry points and route handlers
- `services/` for business logic
- `models/` for structured domain objects
- `utils/` for focused reusable helpers
- `tests/` for automated tests
- `docs/` for project documentation

Guideline:

- Routes should not contain crawling logic
- Services should not contain HTML rendering logic
- Utility functions should stay small and generic
- Shared data structures should live in `models/`

---

## Route Handler Guidelines

Keep route handlers thin.

Route handlers should:

- validate input
- call service-layer functions
- handle success/error responses
- render UI

Route handlers should not:

- implement crawl algorithms
- parse HTML directly
- contain page scoring logic
- generate markdown inline

Good pattern:

```python
def post_generate(request):
    url = validate_url(request)
    result = generation_pipeline.run(url)
    return render_result(result)
```

Bad pattern:

```python
def post_generate(request):
    # validate url
    # fetch pages
    # parse html
    # score pages
    # build markdown
    # render response
```

---

## Service Design Guidelines

Services should encapsulate core behavior.

Each service should have one clear responsibility.

### Crawler service

Responsible for:

- fetching pages
- extracting links
- controlling crawl limits

### Extractor service

Responsible for:

- parsing HTML
- extracting titles and descriptions
- converting raw HTML into structured page data

### Prioritizer service

Responsible for:

- scoring and filtering pages
- selecting the best pages for final output

### Generator service

Responsible for:

- formatting final Markdown
- producing spec-compliant `llms.txt`

Services should communicate through clear typed models rather than loose dictionaries when possible.

---

## Function Design

Functions should do one thing well.

Preferred characteristics:

- small
- predictable
- typed
- easy to test
- minimal side effects

Guidelines:

- Prefer returning values instead of mutating shared state
- Avoid long functions with multiple responsibilities
- Break complex logic into helper functions
- Keep branching shallow where practical

As a rough rule:

- functions over 30–40 lines should be reviewed for possible splitting
- functions with multiple unrelated responsibilities should be refactored

---

## Type Hints

Use type hints broadly.

Examples:

```python
def extract_links(html: str, base_url: str) -> list[str]:
    ...
```

```python
def score_page(page: Page) -> float:
    ...
```

```python
from typing import Iterable

def filter_pages(pages: Iterable[Page]) -> list[Page]:
    ...
```

Type hints improve readability and make coding-agent output more reliable.

---

## Data Models

Prefer structured models for shared data.

Recommended approach:

- Use `@dataclass` for domain entities
- Keep models simple and explicit
- Avoid passing raw dictionaries between multiple layers unless there is a strong reason

Example:

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

Benefits:

- easier to read
- easier to test
- easier to refactor
- fewer key-name mistakes

---

## Error Handling

Handle errors explicitly and gracefully.

Guidelines:

- Catch expected exceptions near the boundary where they occur
- Raise meaningful exceptions for invalid inputs
- Log technical details internally
- Return user-friendly messages from the web layer
- Do not silently swallow important errors

Examples of expected errors:

- invalid URL
- timeout
- request failure
- malformed HTML
- empty crawl results

Good:

```python
try:
    response = await client.get(url, timeout=10)
except httpx.TimeoutException as exc:
    raise CrawlError(f"Timed out fetching {url}") from exc
```

Bad:

```python
try:
    response = await client.get(url)
except Exception:
    pass
```

Avoid broad `except Exception` unless it is truly the correct boundary and the fallback behavior is intentional.

---

## Logging

Use lightweight structured logging where helpful.

Log important lifecycle events such as:

- crawl start
- crawl completion
- page fetch failures
- skipped URLs
- generated page count
- final output generation

Good logging examples:

```python
logger.info("Starting crawl", extra={"url": start_url})
logger.info("Skipping URL outside domain", extra={"url": candidate_url})
logger.info("Generated llms.txt", extra={"page_count": len(selected_pages)})
```

Do not over-log low-value details inside tight loops unless they are useful for debugging.

---

## URL Handling Guidelines

URL bugs are common, so treat URL logic carefully.

Always normalize URLs before comparing or storing them.

Normalization should consider:

- lowercasing scheme and host
- removing fragments
- resolving relative URLs
- handling trailing slashes consistently
- ignoring obvious duplicates
- optionally dropping tracking query parameters

Create dedicated helpers for this logic instead of scattering it throughout the codebase.

Example helpers:

- `normalize_url`
- `is_same_domain`
- `is_html_like_url`
- `should_skip_url`

---

## HTML Parsing Guidelines

Keep HTML parsing robust and defensive.

Guidelines:

- Assume markup may be incomplete or malformed
- Use safe lookup patterns
- Prefer a parser like BeautifulSoup
- Keep extraction logic isolated in the extractor service
- Do not assume required tags always exist

Good:

```python
title = soup.title.string.strip() if soup.title and soup.title.string else ""
```

Bad:

```python
title = soup.title.string.strip()
```

When metadata is missing, apply reasonable fallback behavior.

---

## Asynchronous Code Guidelines

Use async where it improves I/O performance, especially for crawling.

Guidelines:

- Use async HTTP requests for network-bound operations
- Keep async boundaries clear
- Avoid mixing sync and async patterns haphazardly
- Limit concurrency to avoid overload
- Reuse HTTP clients when possible

Good candidates for async:

- page fetching
- robots.txt retrieval
- crawl pipeline network operations

Poor candidates for async:

- simple string formatting
- local scoring logic
- markdown generation

Use async for real I/O, not everywhere by default.

---

## Configuration

Avoid scattering magic numbers through the codebase.

Use configuration objects or named constants for settings such as:

- `MAX_DEPTH`
- `MAX_PAGES`
- `REQUEST_TIMEOUT_SECONDS`
- `MAX_CONCURRENT_REQUESTS`
- `DEFAULT_USER_AGENT`

Good:

```python
@dataclass
class CrawlConfig:
    max_depth: int = 2
    max_pages: int = 50
    timeout_seconds: float = 10.0
```

Bad:

```python
if depth > 2:
    ...
```

Configuration should be easy to find and easy to explain.

---

## Markdown Generation Guidelines

Keep `llms.txt` output deterministic and clean.

Guidelines:

- Use consistent ordering
- Avoid random or unstable output
- Prefer explicit formatting rules
- Omit empty fields gracefully
- Keep descriptions concise
- Escape or sanitize content as needed

Good generator behavior:

- stable section ordering
- stable page ordering within sections
- no duplicate entries
- no malformed markdown

The generator should be easy to inspect and reason about.

---

## Comments and Docstrings

Write comments only when they add value.

Use comments for:

- explaining non-obvious decisions
- documenting tradeoffs
- clarifying tricky edge cases

Do not use comments to restate obvious code.

Bad:

```python
# increment i
i += 1
```

Good:

```python
# Canonical URLs are preferred because many sites expose duplicate
# content under multiple navigation paths.
canonical_url = ...
```

Use docstrings for public functions, classes, and modules when helpful.

Example:

```python
def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication and same-domain comparison."""
```

---

## Testing Standards

Tests are required for important logic.

Focus test coverage on:

- URL normalization
- internal link extraction
- metadata extraction
- prioritization/scoring
- markdown generation
- edge cases and fallback behavior

Test types:

### Unit tests

Test individual functions and services in isolation.

### Integration tests

Test the end-to-end pipeline on a small controlled fixture.

### Edge case tests

Include scenarios such as:

- missing metadata
- malformed HTML
- duplicate URLs
- deep links
- query-heavy URLs
- unreachable pages

Guidelines:

- Keep tests deterministic
- Prefer fixtures over live network dependency where possible
- Use clear names such as `test_normalize_url_removes_fragment`

---

## Preferred Dependency Approach

Keep dependencies minimal and justified.

Use libraries that clearly support the assignment, such as:

- `httpx` for HTTP requests
- `beautifulsoup4` for HTML parsing
- FastHTML for the web layer

Avoid adding heavy dependencies unless they solve a real problem.

For example:

- do not add a database unless you truly need persistence
- do not add a task queue unless the crawl workflow requires background jobs
- do not add frontend complexity unless there is clear user value

This project should feel focused, not over-engineered.

---

## Code Review Heuristics

Before finalizing code, check:

- Is the function doing one thing?
- Are names clear?
- Is the control flow easy to follow?
- Is error handling explicit?
- Is the code easy to test?
- Can the design be explained simply in a project walkthrough?
- Would another engineer understand this quickly?

If the answer is “no,” simplify.

---

## Anti-Patterns to Avoid

Avoid the following:

- giant route handlers
- giant utility files with unrelated helpers
- passing around untyped dictionaries everywhere
- hidden global state
- silent exception swallowing
- copy-pasted logic between services
- premature optimization
- framework-specific magic where plain Python is clearer
- mixing crawling, parsing, scoring, and rendering in one function

This project should look intentional and disciplined.

---

## Suggested Implementation Order

Build in this order:

1. URL utilities and shared models
2. Metadata extractor
3. Crawler
4. Prioritizer
5. Markdown generator
6. Pipeline/orchestration layer
7. FastHTML routes and UI
8. Tests
9. README polish

This order reduces complexity and makes debugging easier.

---

## Guidance for Coding Agents

When generating code for this project:

- prefer explicit, readable implementations
- use type hints
- keep modules focused
- avoid unnecessary abstractions
- do not introduce frameworks or infrastructure not already requested
- preserve separation between routes, services, models, and utils
- write code that a human reviewer can explain confidently

When uncertain, choose the simpler design.

---

## Summary

The codebase should present as:

- clean
- modular
- readable
- disciplined
- easy to test
- easy to explain

Strong fundamentals matter more than cleverness.

A reviewer should be able to open the repository and quickly see thoughtful engineering choices throughout the project.
