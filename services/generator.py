"""Markdown generator for producing `llms.txt` output."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from urllib.parse import urlsplit

from models.page import Page

SECTION_PRIORITY: dict[str, int] = {
    "Documentation": 0,
    "Resources": 1,
    "Product": 2,
    "Company": 3,
    "Support": 4,
    "Other": 5,
}


def generate_llms_txt(pages: list[Page]) -> str:
    """Return a deterministic `llms.txt` Markdown document for the given pages."""

    if not pages:
        return "# Website"

    sorted_pages = _sort_pages(pages)
    site_title = _select_site_title(sorted_pages)
    site_summary = _select_site_summary(sorted_pages)
    section_pages = _group_pages(sorted_pages)

    lines: list[str] = [f"# {site_title}"]
    if site_summary:
        lines.extend(["", f"> {site_summary}"])

    for section_name, grouped_pages in section_pages:
        lines.extend(["", f"## {section_name}"])
        lines.extend(_format_page_bullet(page) for page in grouped_pages)

    return "\n".join(lines)


def _sort_pages(pages: Iterable[Page]) -> list[Page]:
    return sorted(
        pages,
        key=lambda page: (
            not page.is_homepage,
            -page.score,
            page.path_depth,
            page.title.lower(),
            page.effective_url,
        ),
    )


def _select_site_title(pages: list[Page]) -> str:
    homepage = next((page for page in pages if page.is_homepage and page.title), None)
    if homepage is not None:
        return homepage.title

    titled_page = next((page for page in pages if page.title), None)
    if titled_page is not None:
        return titled_page.title

    hostname = urlsplit(pages[0].effective_url).hostname or "Website"
    return hostname.removeprefix("www.").split(".")[0].replace("-", " ").title()


def _select_site_summary(pages: list[Page]) -> str | None:
    homepage = next((page for page in pages if page.is_homepage and page.description), None)
    if homepage is not None:
        return homepage.description

    descriptive_page = next((page for page in pages if page.description), None)
    if descriptive_page is not None:
        return descriptive_page.description

    return None


def _group_pages(pages: list[Page]) -> list[tuple[str, list[Page]]]:
    grouped_pages: dict[str, list[Page]] = defaultdict(list)
    content_pages = [page for page in pages if not page.is_homepage]

    pages_to_group = content_pages or pages
    for page in pages_to_group:
        grouped_pages[_select_section(page)].append(page)

    return sorted(
        (
            (
                section_name,
                sorted(
                    grouped_section_pages,
                    key=lambda page: (
                        page.path_depth,
                        -page.score,
                        page.title.lower(),
                        page.effective_url,
                    ),
                ),
            )
            for section_name, grouped_section_pages in grouped_pages.items()
        ),
        key=lambda item: (SECTION_PRIORITY[item[0]], item[0]),
    )


def _select_section(page: Page) -> str:
    if page.category:
        normalized_category = page.category.strip().title()
        if normalized_category in SECTION_PRIORITY:
            return normalized_category

    path = page.path.lower()
    if any(token in path for token in ("/docs", "/guide", "/api", "/reference", "/tutorial")):
        return "Documentation"
    if any(token in path for token in ("/blog", "/news", "/resources", "/learn")):
        return "Resources"
    if any(token in path for token in ("/pricing", "/features", "/product", "/solutions")):
        return "Product"
    if any(token in path for token in ("/about", "/company", "/careers")):
        return "Company"
    if any(token in path for token in ("/support", "/contact", "/help", "/faq")):
        return "Support"

    return "Other"


def _format_page_bullet(page: Page) -> str:
    bullet = f"- [{page.title}]({page.effective_url})"
    if page.description:
        return f"{bullet}: {page.description}"
    return bullet
