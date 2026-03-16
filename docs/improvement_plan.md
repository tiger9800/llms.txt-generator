# Improvement Plan for llms.txt Generator

## Goal

Improve the system along three axes:

1.  Usability
2.  Performance
3.  Output quality and evaluation

The improvements are organized into tiers so that the highest‑impact
changes are implemented first.

------------------------------------------------------------------------

# Tier 1 --- High Impact Improvements

These changes significantly improve the product and engineering
robustness.

------------------------------------------------------------------------

## 1. Detect Existing llms.txt

Before crawling a website, check whether the site already provides:

    https://domain.com/llms.txt

### Behavior

If the file exists:

1.  Fetch it
2.  Display it to the user
3.  Offer options:

-   Use existing llms.txt
-   Regenerate llms.txt

UI toggle:

    [ ] Force regenerate even if llms.txt exists

### Benefits

-   avoids unnecessary crawling
-   improves usability
-   allows inspection of existing implementations

### Implementation Notes

-   Perform a simple HTTP GET
-   Follow redirects
-   Treat non‑200 responses as "not found"

------------------------------------------------------------------------

## 2. Concurrent BFS Crawling

Sequential crawling becomes slow on larger websites.

Introduce bounded concurrency while preserving BFS structure.

### Current algorithm

    sequential BFS

### Improved algorithm

    layered concurrent BFS

### Strategy

1.  Maintain BFS depth levels
2.  Fetch pages at the same depth concurrently
3.  Extract links
4.  Enqueue next‑level links

### Constraints

-   max_depth
-   max_pages
-   max_concurrent_requests

Recommended defaults:

    max_depth = 2
    max_pages = 50
    max_concurrent_requests = 5

### Implementation

Use:

-   httpx.AsyncClient
-   asyncio.Semaphore

### Benefits

-   faster crawl times
-   predictable behavior
-   easier to reason about

------------------------------------------------------------------------

## 3. Evaluation Against Known Sites

Evaluate generator quality by comparing outputs with sites that already
publish llms.txt.

### Example sites

-   firecrawl.dev
-   documentation sites
-   open‑source project docs

### Evaluation Metrics

-   URL overlap
-   section similarity
-   description coverage
-   page recall

### Evaluation Harness

Create:

    tests/evaluation/run_eval.py

### Process

1.  Fetch existing llms.txt
2.  Generate new llms.txt
3.  Compare URL sets
4.  Report precision and recall

### Benefits

-   demonstrates engineering rigor
-   validates prioritization heuristics
-   improves output quality

------------------------------------------------------------------------

# Tier 2 --- Product Improvements

These features improve usability but are not required for the core
system.

------------------------------------------------------------------------

## 4. Advanced Crawl Configuration

Allow users to configure crawl parameters.

### UI

Advanced Options:

-   max_depth
-   max_pages
-   request_timeout
-   max_concurrency

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

------------------------------------------------------------------------

# Tier 3 --- Optional AI Enhancements

These features are optional and should be implemented after the
deterministic system is stable.

------------------------------------------------------------------------

## 5. AI‑Generated Descriptions

Some pages lack meaningful descriptions.

Allow optional LLM‑based description generation.

### Behavior

If page.description is missing:

    generate summary using LLM

### UI Option

    [ ] Enhance descriptions with AI

### Guidelines

-   only generate descriptions when missing
-   limit token usage
-   cache generated descriptions
-   clearly mark generated descriptions in debug output

### Benefits

-   improves final llms.txt readability
-   improves usefulness for LLM consumers

------------------------------------------------------------------------

# Additional Improvements

------------------------------------------------------------------------

## Sitemap Support

Before crawling, check:

    /sitemap.xml

If present:

1.  Parse URLs
2.  Seed crawler with sitemap entries

### Benefits

-   faster discovery
-   better coverage
-   less crawling required

------------------------------------------------------------------------

## Debug / Explainability Output

Expose reasoning behind page selection.

Example debug output:

    /docs/api
    score: 0.92
    reasons:
      - shallow path
      - docs keyword
      - high‑quality metadata

### Benefits

-   improves transparency
-   helps debugging prioritization
-   useful for demos

------------------------------------------------------------------------

# Implementation Order

Recommended order:

1.  Existing llms.txt detection
2.  Concurrent BFS crawler
3.  Evaluation harness
4.  Crawl configuration options
5.  Sitemap support
6.  AI description generation
7.  Debug / explainability output

------------------------------------------------------------------------

# Coding Agent Guidance

When implementing improvements:

-   follow docs/coding_guidelines.md

-   respect architecture defined in docs/architecture.md

-   avoid unnecessary dependencies

-   maintain separation between:

    services models utils app

All new features should include:

-   unit tests
-   clear type hints
-   small focused functions

Prefer deterministic logic unless AI assistance is explicitly required.

------------------------------------------------------------------------

# Summary

The project should evolve along three axes:

    Usability
    Performance
    Evaluation

By implementing these improvements, the system will become:

-   faster
-   more reliable
-   easier to validate
-   more useful as a real‑world tool
