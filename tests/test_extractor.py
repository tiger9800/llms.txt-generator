from __future__ import annotations

from services.extractor import DEFAULT_DESCRIPTION, extract_page, extract_pages


def test_extract_page_reads_primary_metadata_fields() -> None:
    html = """
    <html>
      <head>
        <title>Getting Started</title>
        <meta name="description" content="Learn how to get started quickly.">
        <link rel="canonical" href="/docs/start/">
      </head>
      <body>
        <h1>Welcome</h1>
      </body>
    </html>
    """

    page = extract_page("https://example.com/docs/start/?utm_source=newsletter", html, 1)

    assert page.url == "https://example.com/docs/start"
    assert page.title == "Getting Started"
    assert page.description == "Learn how to get started quickly."
    assert page.path == "/docs/start"
    assert page.depth == 1
    assert page.canonical_url == "https://example.com/docs/start"


def test_extract_page_uses_safe_fallbacks_when_metadata_is_missing() -> None:
    html = """
    <html>
      <body>
        <main>
          <p>Build integrations faster with our API guides and examples.</p>
          <p>Everything you need to ship a working prototype is documented here.</p>
        </main>
      </body>
    </html>
    """

    page = extract_page("https://example.com/docs/api-reference/", html, 2)

    assert page.title == "Api Reference"
    assert page.description.startswith("Build integrations faster with our API guides")
    assert page.canonical_url == "https://example.com/docs/api-reference"
    assert page.path == "/docs/api-reference"


def test_extract_page_handles_malformed_html_and_invalid_canonical_url() -> None:
    html = """
    <html>
      <head>
        <title>Broken <b>Page<title>
        <meta name="description" content="">
        <link rel="canonical" href="::not a valid canonical::">
      </head>
      <body>
        <p>Malformed markup should still produce usable text output.
    """

    page = extract_page("https://example.com/broken-page", html, 0)

    assert page.title == "Broken Page"
    assert "Malformed markup should still produce usable text output." in page.description
    assert page.canonical_url == "https://example.com/broken-page"


def test_extract_page_returns_default_description_when_no_text_is_available() -> None:
    html = "<html><head></head><body><script>ignored()</script></body></html>"

    page = extract_page("https://example.com/", html, 0)

    assert page.title == "Example"
    assert page.description == DEFAULT_DESCRIPTION


def test_extract_pages_returns_page_models_for_batch_inputs() -> None:
    pages = extract_pages(
        [
            ("https://example.com/", "<html><head><title>Home</title></head></html>", 0),
            ("https://example.com/docs", "<html><body><p>Docs overview</p></body></html>", 1),
        ]
    )

    assert len(pages) == 2
    assert [page.title for page in pages] == ["Home", "Docs"]
