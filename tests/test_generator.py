from __future__ import annotations

from models.page import Page
from services.generator import generate_llms_txt


def test_generate_llms_txt_builds_title_summary_and_sections() -> None:
    pages = [
        Page(
            url="https://example.com/",
            title="Example Platform",
            description="Developer tools and documentation for Example Platform.",
            path="/",
            depth=0,
        ),
        Page(
            url="https://example.com/docs/start",
            title="Getting Started",
            description="Introduction to the platform.",
            path="/docs/start",
            depth=1,
        ),
        Page(
            url="https://example.com/blog",
            title="Blog",
            description="Product updates and tutorials.",
            path="/blog",
            depth=1,
        ),
    ]

    markdown = generate_llms_txt(pages)

    assert markdown.startswith("# Example Platform\n\n> Developer tools and documentation")
    assert "## Documentation" in markdown
    assert "## Resources" in markdown
    assert "- [Getting Started](https://example.com/docs/start): Introduction to the platform." in markdown
    assert "- [Blog](https://example.com/blog): Product updates and tutorials." in markdown


def test_generate_llms_txt_omits_empty_descriptions_gracefully() -> None:
    pages = [
        Page(
            url="https://example.com/",
            title="Example",
            description="",
            path="/",
            depth=0,
        ),
        Page(
            url="https://example.com/support",
            title="Support",
            description="",
            path="/support",
            depth=1,
        ),
    ]

    markdown = generate_llms_txt(pages)

    assert "> " not in markdown
    assert "- [Support](https://example.com/support)" in markdown
    assert "- [Support](https://example.com/support):" not in markdown


def test_generate_llms_txt_uses_deterministic_ordering_within_sections() -> None:
    pages = [
        Page(
            url="https://example.com/",
            title="Example",
            description="Platform overview.",
            path="/",
            depth=0,
        ),
        Page(
            url="https://example.com/docs/reference",
            title="API Reference",
            description="Reference docs.",
            path="/docs/reference",
            depth=1,
            score=5.0,
        ),
        Page(
            url="https://example.com/docs/start",
            title="Getting Started",
            description="Start here.",
            path="/docs/start",
            depth=1,
            score=10.0,
        ),
        Page(
            url="https://example.com/docs/advanced/configuration",
            title="Configuration",
            description="Configure the platform.",
            path="/docs/advanced/configuration",
            depth=2,
            score=20.0,
        ),
    ]

    markdown = generate_llms_txt(pages)

    getting_started_index = markdown.index("- [Getting Started](https://example.com/docs/start): Start here.")
    api_reference_index = markdown.index(
        "- [API Reference](https://example.com/docs/reference): Reference docs."
    )
    configuration_index = markdown.index(
        "- [Configuration](https://example.com/docs/advanced/configuration): Configure the platform."
    )

    assert getting_started_index < api_reference_index < configuration_index


def test_generate_llms_txt_uses_category_when_available() -> None:
    pages = [
        Page(
            url="https://example.com/",
            title="Example",
            description="Platform overview.",
            path="/",
            depth=0,
        ),
        Page(
            url="https://example.com/customers",
            title="Customers",
            description="Customer stories.",
            path="/customers",
            depth=1,
            category="Resources",
        ),
    ]

    markdown = generate_llms_txt(pages)

    assert "## Resources" in markdown
    assert "- [Customers](https://example.com/customers): Customer stories." in markdown


def test_generate_llms_txt_handles_empty_input() -> None:
    assert generate_llms_txt([]) == "# Website"
