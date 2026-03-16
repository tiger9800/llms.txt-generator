# Improvement Plan for llms.txt Generator

## Goal

Improve the system along three axes:

1.  Usability
2.  Performance
3.  Output quality and evaluation

The improvements are organized into tiers so that the highest-impact
changes are implemented first.

------------------------------------------------------------------------

# Tier 1 --- High Impact Improvements

These changes significantly improve the product and engineering
robustness.

------------------------------------------------------------------------

## 1. Existing `llms.txt` Detection

Status: implemented.

The pipeline now checks for an existing `llms.txt` before crawling and
surfaces it in the UI when found.

### Current behavior

Candidate locations:

    https://domain.com/llms.txt
    https://domain.com/subpath/llms.txt

If an existing file is found:

1.  Fetch it
2.  Display it to the user
3.  Allow the user to force generate instead of using the existing file

UI toggle:

    [ ] Force generate even if llms.txt exists

### Implementation notes

-   perform a simple HTTP GET
-   follow redirects
-   treat non-200 responses as "not found"
-   try a path-local `llms.txt` first for subpath roots, then fall back
    to the domain root
-   report the actual detected `llms.txt` source URL in the result

------------------------------------------------------------------------

## 2. Concurrent BFS Crawling

Status: implemented.

The crawler now uses layered concurrent BFS while preserving depth-based
ordering.

### Current behavior

    layered concurrent BFS

### Strategy

1.  Maintain BFS depth levels
2.  Fetch pages at the same depth concurrently
3.  Extract links
4.  Enqueue next-level links

### Constraints

-   `max_depth`
-   `max_pages`
-   `max_concurrent_requests`

Recommended defaults:

    max_depth = 2
    max_pages = 50
    max_concurrent_requests = 5

### Implementation

Use:

-   `httpx.AsyncClient`
-   `asyncio.Semaphore`

### Benefits

-   faster crawl times
-   predictable behavior
-   easier to reason about
-   preserves a clear crawl order by depth

------------------------------------------------------------------------

## 3. `robots.txt` Support

The crawler should behave responsibly and respect site-level crawl
rules.

Before fetching crawl targets, check:

    https://domain.com/robots.txt

### Behavior

-   fetch and parse `robots.txt`

-   determine whether a URL is allowed before crawling it

-   skip disallowed URLs

-   use a custom user-agent such as:

    llmstxt-generator/1.0

### Implementation Notes

Recommended implementation:

-   `urllib.robotparser` for parsing

-   a small helper module such as:

    utils/robots.py

### Failure Handling

If `robots.txt` cannot be fetched or parsed:

-   fail open
-   continue crawling
-   log the failure

This prevents the entire crawl from failing due to temporary
`robots.txt` issues.

### Benefits

-   demonstrates responsible crawler design
-   improves engineering maturity
-   prevents crawling obviously disallowed paths

------------------------------------------------------------------------

## 4. Evaluation Harness

Evaluate generator quality by comparing outputs with sites that already
publish `llms.txt`.

### Example sites

-   `firecrawl.dev`
-   documentation sites
-   open-source project docs
-   other public sites with existing `llms.txt`

### Evaluation Metrics

-   URL overlap
-   section similarity
-   description coverage
-   page recall
-   page precision

### Evaluation Harness

Create:

    tests/evaluation/run_eval.py

### Process

1.  Fetch existing `llms.txt`
2.  Generate a new `llms.txt`
3.  Compare URL sets
4.  Report precision and recall
5.  Inspect qualitative differences in selected pages and descriptions

### Benefits

-   demonstrates engineering rigor
-   validates prioritization heuristics
-   improves output quality
-   gives a repeatable way to evaluate improvements

------------------------------------------------------------------------

# Tier 2 --- Product and Crawl Improvements

These features improve usability and crawl quality but are not required
for the initial core system.

------------------------------------------------------------------------

## 5. Crawl Configuration

Allow users to configure crawl parameters.

### UI

Advanced Options:

-   `max_depth`
-   `max_pages`
-   `request_timeout`
-   `max_concurrency`

Example defaults:

    max_depth = 2
    max_pages = 50
    timeout_seconds = 10
    max_concurrency = 5

### Implementation

Create:

    models/crawl_config.py

Example:

    from dataclasses import dataclass

    @dataclass
    class CrawlConfig:
        max_depth: int = 2
        max_pages: int = 50
        timeout_seconds: float = 10
        max_concurrency: int = 5

### Benefits

-   gives users more control
-   helps with testing and benchmarking
-   makes the tool more flexible without changing core logic

------------------------------------------------------------------------

## 6. Sitemap Support

Before crawling deeply, check for sitemap availability.

Primary path:

    /sitemap.xml

Also consider sitemap declarations inside `robots.txt`.

### Behavior

If a sitemap is present:

1.  Parse sitemap URLs
2.  Seed the crawler with sitemap entries
3.  Prefer sitemap-discovered URLs as high-quality crawl seeds

### Benefits

-   faster discovery
-   better coverage
-   less crawling required
-   often improves recall on documentation-heavy sites

### Implementation Notes

-   keep sitemap parsing simple for V1
-   support standard XML sitemap format
-   treat sitemap seeding as an enhancement, not a hard dependency

------------------------------------------------------------------------

# Tier 3 --- Optional AI Enhancements

These features are optional and should be implemented after the
deterministic system is stable.

------------------------------------------------------------------------

## 7. AI-Generated Descriptions

Some pages lack meaningful descriptions.

Allow optional LLM-based description generation.

### Behavior

If `page.description` is missing or clearly low quality:

    generate summary using LLM

### UI Option

    [ ] Enhance descriptions with AI

### Guidelines

-   only generate descriptions when missing or poor
-   limit token usage
-   cache generated descriptions where practical
-   clearly mark generated descriptions in debug output
-   keep deterministic extraction as the default behavior

### Benefits

-   improves final `llms.txt` readability
-   improves usefulness for LLM consumers
-   fills in gaps on sites with poor metadata

### Risks

-   increased latency
-   increased cost
-   less deterministic output
-   possible hallucinated descriptions

Because of these tradeoffs, AI enhancement should remain optional.

------------------------------------------------------------------------

# Implementation Order

Recommended order:

1.  existing `llms.txt` detection
2.  concurrent BFS crawler
3.  `robots.txt` support
4.  evaluation harness
5.  crawl configuration
6.  sitemap support
7.  AI description generation

This order ensures that:

-   core functionality improves first
-   crawl performance and crawl hygiene are addressed early
-   evaluation is available before optional AI features
-   optional AI enhancements are implemented last

------------------------------------------------------------------------

# Coding Agent Guidance

When implementing improvements:

-   follow `docs/coding_guidelines.md`

-   respect architecture defined in `docs/architecture.md`

-   avoid unnecessary dependencies

-   maintain separation between:

    services models utils app

All new features should include:

-   unit tests
-   clear type hints
-   small focused functions
-   explicit error handling

Prefer deterministic logic unless AI assistance is explicitly required.

------------------------------------------------------------------------

# Suggested File Targets

Likely files to add or update:

-   `services/crawler.py`
-   `services/pipeline.py`
-   `services/generator.py`
-   `models/crawl_config.py`
-   `utils/robots.py`
-   `utils/sitemap.py`
-   `tests/test_crawler.py`
-   `tests/test_pipeline.py`
-   `tests/evaluation/run_eval.py`

------------------------------------------------------------------------

# Summary

The project should evolve along three axes:

    Usability
    Performance
    Evaluation

By implementing these improvements, the system will become:

-   faster
-   more reliable
-   more respectful of crawl constraints
-   easier to validate
-   more useful as a real-world tool
