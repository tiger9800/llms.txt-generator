# UI and Product Improvements

This document describes improvements discovered after deploying the
application and testing the real user experience.

These improvements focus on:

-   crawl transparency
-   usability
-   demo quality
-   reviewer experience

They do **not change the crawler architecture**.

They improve how the system is **observed and interacted with**.

------------------------------------------------------------------------

# 1. Crawl Progress Indicator

Status: implemented.

Generation now runs as a background job and shows live crawl progress in
the UI while the pipeline is running.

Current UI:

-   progress page is shown immediately after submission
-   crawler progress is polled from a lightweight JSON endpoint
-   the page displays:
    -   current crawl target
    -   current depth
    -   pages visited
    -   pages queued
-   when generation finishes, the UI redirects to the result page
-   if generation fails, the progress page shows a friendly failure
    state and a path back home

Example UI:

Crawling https://example.com

Depth: 1 Pages visited: 12 Pages queued: 7

Benefits:

-   improves perceived performance
-   makes the crawler easier to understand
-   improves demo quality

Implementation ideas:

-   expose crawler progress events
-   surface them through a background generation job
-   poll the job status from the UI
-   keep the route layer thin by storing only job state in the web layer

Likely files:

services/crawler.py services/pipeline.py app/routes.py app/views.py

------------------------------------------------------------------------

# 2. Crawl Summary Panel

Status: implemented.

After generation finishes, the result page now displays a compact crawl
summary panel when generation was produced from a crawl rather than an
existing `llms.txt`.

Current UI:

-   shows a dedicated `Crawl Summary` section on the result page
-   displays:
    -   pages crawled
    -   depth reached
    -   total crawl time
-   omits the panel when an existing `llms.txt` was used and no crawl
    happened

Example output:

Crawl Summary

Pages crawled: 27 Depth reached: 2 Total crawl time: 1.8 seconds

Benefits:

-   improves transparency
-   demonstrates crawler quality
-   helps debugging

Implementation notes:

-   reuse pipeline result data rather than recomputing statistics in the
    view layer
-   keep the web layer focused on rendering
-   defer `robots.txt` skip counts to the separate robots debug item
    since that tracking is not yet exposed in the pipeline

------------------------------------------------------------------------

# 3. Output Copy Button

Status: implemented.

The result page now includes a copy button for the generated
`llms.txt` preview.

Current UI:

-   a `Copy llms.txt` button appears next to the download button
-   it copies the rendered preview contents from the result page
-   the UI shows lightweight inline feedback after the copy attempt

Example:

\[ Copy llms.txt \]

Benefits:

-   improves usability
-   makes the tool easier to use in practice

Implementation notes:

-   keep the feature entirely in the result-page view layer
-   reuse the already-rendered preview instead of generating a second
    copy source
-   avoid new dependencies and use the browser clipboard API directly

------------------------------------------------------------------------

# 4. Error Display Improvements

Improve error messages when generation fails.

Examples:

Instead of:

Error

Show:

Site blocked by bot protection.

Possible causes:

-   Cloudflare protection
-   JavaScript-only site
-   CAPTCHA

Benefits:

-   improves UX
-   reduces confusion

------------------------------------------------------------------------

# 5. Loading State Improvements

Show a loading indicator during generation.

Example:

Generating llms.txt...

Benefits:

-   improves perceived responsiveness
-   avoids confusion during long crawls

------------------------------------------------------------------------

# Implementation Order

Recommended order:

1.  Crawl summary panel
2.  Example input URLs
3.  Copy output button
4.  Download output option
5.  Robots debug output
6.  Crawl progress indicator
7.  Improved error display
8.  Loading state improvements

------------------------------------------------------------------------

# Coding Guidance

These improvements should:

-   avoid changing crawler core logic
-   reuse existing pipeline data
-   focus on UI improvements

Prefer:

-   small UI components
-   minimal new dependencies
-   clear separation between backend and UI logic
