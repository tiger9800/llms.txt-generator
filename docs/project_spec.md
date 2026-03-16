# Automated llms.txt Generator

## Overview

This project is a web application that generates a standards-compliant
`llms.txt` file for any public website.

A user provides a website URL, and the application:

1.  Crawls the website
2.  Extracts important pages and metadata
3.  Organizes the information into the `llms.txt` format
4.  Returns a generated `llms.txt` file that the user can preview or
    download

The goal is to help websites automatically create structured summaries
that are optimized for large language models (LLMs).

The `llms.txt` file is a Markdown document placed at `/llms.txt` on a
website that summarizes important content and provides structured links
to key pages for AI systems.

------------------------------------------------------------------------

# Goals

The application should:

-   Accept a website URL from a user
-   Crawl the website safely
-   Extract titles, descriptions, and URLs
-   Identify the most important pages
-   Generate a valid `llms.txt` file
-   Display and allow downloading of the generated file

## Non-goals

-   Full web indexing
-   SEO analysis
-   Deep semantic page analysis

------------------------------------------------------------------------

# High-Level Architecture

    User
     ↓
    FastHTML Web App
     ↓
    Crawler Service
     ↓
    Metadata Extractor
     ↓
    Page Prioritizer
     ↓
    llms.txt Generator

------------------------------------------------------------------------

# Components

## Web App

Handles the UI and user interaction.

Responsibilities:

-   Accept URL input
-   Trigger generation
-   Show results
-   Provide download

Framework:

-   FastHTML

------------------------------------------------------------------------

## Crawler Service

Responsible for discovering pages on the website.

Responsibilities:

-   Fetch HTML pages
-   Extract internal links
-   Avoid duplicate visits
-   Limit crawl depth

Expected behavior:

-   Crawl only within the same domain
-   Use breadth-first search (BFS)
-   Limit crawl depth (default: 2--3)
-   Limit total pages (default: 50--100)

------------------------------------------------------------------------

## Metadata Extractor

Extract useful metadata from each crawled page.

Fields to extract:

-   Page title
-   Meta description
-   Canonical URL
-   Page path

HTML elements used:

``` html
<title>
<meta name="description">
<link rel="canonical">
```

Fallback rules:

-   If description missing → generate short summary from page text
-   If canonical missing → use fetched URL

------------------------------------------------------------------------

## Page Prioritizer

The crawler may find many pages.\
This component decides which pages appear in the final `llms.txt`.

Possible ranking signals:

-   Homepage
-   Short URL paths
-   Navigation links
-   Documentation sections
-   Blog / resources

Limit final list to:

20--50 important pages

------------------------------------------------------------------------

## llms.txt Generator

Converts extracted information into a Markdown file that follows the
`llms.txt` specification.

Example output:

    # Example Website
    > Official documentation and resources for Example product.

    Example provides tools for developers to build scalable applications.

    ## Documentation

    - [Getting Started](https://example.com/docs/start): Introduction to the platform
    - [API Reference](https://example.com/docs/api): Complete API documentation

    ## Resources

    - [Blog](https://example.com/blog): Latest updates and tutorials
    - [Support](https://example.com/support): Help and troubleshooting

Formatting rules:

-   H1 title for site name
-   Blockquote summary
-   H2 sections for categories
-   Bullet lists of links

Format:

    [Page Title](URL): Description

------------------------------------------------------------------------

# Data Flow

    User enters URL
     ↓
    Backend receives request
     ↓
    Crawler discovers pages
     ↓
    Metadata extracted
     ↓
    Pages ranked / filtered
     ↓
    Markdown llms.txt generated
     ↓
    Result returned to UI

------------------------------------------------------------------------

# Project Structure

    llms-txt-generator/

    docs/
      project_spec.md

    app/
      main.py
      routes.py

    services/
      crawler.py
      extractor.py
      prioritizer.py
      generator.py

    models/
      page.py

    utils/
      url_utils.py
      http_utils.py

    static/
    templates/

    tests/

------------------------------------------------------------------------

# Core Data Model

## Page

Represents a crawled page.

    class Page:
        url: str
        title: str
        description: str
        path: str
        depth: int

------------------------------------------------------------------------

# Key Algorithms

## Crawling Strategy

Breadth-first search:

    queue = [homepage]

    while queue not empty:
        pop page
        fetch HTML
        extract links
        add unseen links to queue

Constraints:

-   Same domain only
-   Maximum crawl depth
-   Maximum pages

------------------------------------------------------------------------

## Duplicate Prevention

Use a visited set:

    visited_urls = set()

Normalize URLs before storing.

------------------------------------------------------------------------

# Performance Considerations

Use asynchronous HTTP requests.

Recommended library:

    httpx

Benefits:

-   Faster crawling
-   Non-blocking requests

------------------------------------------------------------------------

# Safety Considerations

The crawler should:

-   Respect robots.txt if possible
-   Apply request timeouts
-   Avoid infinite loops
-   Limit request rate

------------------------------------------------------------------------

# Web UI

Minimal interface.

Homepage:

    Enter website URL
    [Generate llms.txt]

Results page:

    Preview generated llms.txt
    [Download file]

Optional enhancements:

-   Crawl progress
-   Page preview
-   Error messages

------------------------------------------------------------------------

# Future Improvements

Potential extensions:

-   `llms-full.txt` generation
-   Sitemap integration
-   AI-based page summarization
-   Crawl visualization
-   Caching previous crawls
