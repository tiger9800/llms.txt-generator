"""Evaluation harness for comparing generated output with existing llms.txt files."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
from typing import Protocol

import httpx

from services.pipeline import GenerationPipeline, GenerationResult
from utils.http_utils import get_async_client
from utils.url_utils import normalize_url

_SECTION_RE = re.compile(r"^##\s+(?P<section>.+?)\s*$")
_BULLET_RE = re.compile(
    r"^- \[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)(?::\s*(?P<description>.+))?$"
)
DEFAULT_SITES_FILE = Path(__file__).with_name("sites.txt")


@dataclass(slots=True)
class EvalEntry:
    """Structured representation of one page entry in an llms.txt file."""

    title: str
    url: str
    description: str | None
    section: str


@dataclass(slots=True)
class EvalMetrics:
    """Summary metrics for comparing generated and existing llms.txt files."""

    generated_url_count: int
    existing_url_count: int
    overlap_url_count: int
    generated_slug_count: int
    existing_slug_count: int
    overlap_slug_count: int
    generated_title_count: int
    existing_title_count: int
    overlap_title_count: int
    precision: float
    recall: float
    slug_precision: float
    slug_recall: float
    title_precision: float
    title_recall: float
    generated_description_coverage: float
    existing_description_coverage: float
    section_similarity: float


@dataclass(slots=True)
class EvalReport:
    """Full evaluation report for one site."""

    root_url: str
    existing_llms_txt_url: str
    existing_markdown: str
    generated_result: GenerationResult
    metrics: EvalMetrics
    generated_entries: list[EvalEntry]
    existing_entries: list[EvalEntry]
    generated_only_titles: list[str]
    existing_only_titles: list[str]


class EvalPipeline(Protocol):
    """Minimal protocol for objects that can produce a GenerationResult."""

    async def run(
        self,
        root_url: str,
        *,
        force_generate: bool = True,
        respect_robots_txt: bool = True,
    ) -> GenerationResult:
        """Execute the generation pipeline for evaluation."""
        ...


def parse_llms_txt(markdown: str) -> list[EvalEntry]:
    """Parse page entries from an llms.txt Markdown document."""

    entries: list[EvalEntry] = []
    current_section = "Other"

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        section_match = _SECTION_RE.match(line)
        if section_match is not None:
            current_section = section_match.group("section")
            continue

        bullet_match = _BULLET_RE.match(line)
        if bullet_match is None:
            continue

        entries.append(
            EvalEntry(
                title=bullet_match.group("title").strip(),
                url=normalize_url(bullet_match.group("url").strip()),
                description=_normalize_optional_text(bullet_match.group("description")),
                section=current_section,
            )
        )

    return entries


def compare_llms_txt(generated_markdown: str, existing_markdown: str) -> EvalMetrics:
    """Compare generated and existing llms.txt strings and return summary metrics."""

    generated_entries = parse_llms_txt(generated_markdown)
    existing_entries = parse_llms_txt(existing_markdown)
    generated_urls = {entry.url for entry in generated_entries}
    existing_urls = {entry.url for entry in existing_entries}
    generated_slugs = {_normalize_url_slug(entry.url) for entry in generated_entries}
    existing_slugs = {_normalize_url_slug(entry.url) for entry in existing_entries}
    generated_titles = {_normalize_title(entry.title) for entry in generated_entries}
    existing_titles = {_normalize_title(entry.title) for entry in existing_entries}
    overlap_urls = generated_urls & existing_urls
    overlap_slugs = generated_slugs & existing_slugs
    overlap_titles = generated_titles & existing_titles

    return EvalMetrics(
        generated_url_count=len(generated_urls),
        existing_url_count=len(existing_urls),
        overlap_url_count=len(overlap_urls),
        generated_slug_count=len(generated_slugs),
        existing_slug_count=len(existing_slugs),
        overlap_slug_count=len(overlap_slugs),
        generated_title_count=len(generated_titles),
        existing_title_count=len(existing_titles),
        overlap_title_count=len(overlap_titles),
        precision=_safe_ratio(len(overlap_urls), len(generated_urls)),
        recall=_safe_ratio(len(overlap_urls), len(existing_urls)),
        slug_precision=_safe_ratio(len(overlap_slugs), len(generated_slugs)),
        slug_recall=_safe_ratio(len(overlap_slugs), len(existing_slugs)),
        title_precision=_safe_ratio(len(overlap_titles), len(generated_titles)),
        title_recall=_safe_ratio(len(overlap_titles), len(existing_titles)),
        generated_description_coverage=_description_coverage(generated_entries),
        existing_description_coverage=_description_coverage(existing_entries),
        section_similarity=_section_similarity(generated_entries, existing_entries),
    )


async def evaluate_site(
    root_url: str,
    *,
    pipeline: EvalPipeline | None = None,
    client: httpx.AsyncClient | None = None,
    force_generate: bool = True,
    respect_robots_txt: bool = True,
) -> EvalReport:
    """Run the pipeline and compare its output to an existing llms.txt file."""

    normalized_root_url = normalize_url(root_url)
    existing_llms_txt_url, existing_llms_txt = await _fetch_existing_llms_txt(
        normalized_root_url,
        client=client,
    )
    active_pipeline = pipeline or GenerationPipeline(client=client)
    generated_result = await active_pipeline.run(
        normalized_root_url,
        force_generate=force_generate,
        respect_robots_txt=respect_robots_txt,
    )

    generated_entries = parse_llms_txt(generated_result.llms_txt_markdown)
    existing_entries = parse_llms_txt(existing_llms_txt)
    metrics = compare_llms_txt(generated_result.llms_txt_markdown, existing_llms_txt)
    generated_only_titles, existing_only_titles = _diff_titles(
        generated_entries,
        existing_entries,
    )
    return EvalReport(
        root_url=normalized_root_url,
        existing_llms_txt_url=existing_llms_txt_url,
        existing_markdown=existing_llms_txt,
        generated_result=generated_result,
        metrics=metrics,
        generated_entries=generated_entries,
        existing_entries=existing_entries,
        generated_only_titles=generated_only_titles,
        existing_only_titles=existing_only_titles,
    )


async def _fetch_existing_llms_txt(
    root_url: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> tuple[str, str]:
    async with get_async_client(client, follow_redirects=True, timeout=10.0) as active_client:
        for candidate_url in _candidate_llms_txt_urls(root_url):
            try:
                response = await active_client.get(candidate_url)
            except httpx.HTTPError:
                continue

            if response.status_code == 200:
                return candidate_url, response.text

    raise ValueError(f"No existing llms.txt found for {root_url}.")


def format_eval_report(
    report: EvalReport,
    *,
    show_markdown: bool = False,
    show_all_diffs: bool = False,
) -> str:
    """Render a compact text report for console use."""

    metrics = report.metrics
    lines = [
        f"Root URL: {report.root_url}",
        f"Existing llms.txt: {report.existing_llms_txt_url}",
        f"Generated URLs: {metrics.generated_url_count}",
        f"Existing URLs: {metrics.existing_url_count}",
        f"URL overlap: {metrics.overlap_url_count}",
        f"Precision: {metrics.precision:.2%}",
        f"Recall: {metrics.recall:.2%}",
        f"Generated slugs: {metrics.generated_slug_count}",
        f"Existing slugs: {metrics.existing_slug_count}",
        f"Slug overlap: {metrics.overlap_slug_count}",
        f"Slug precision: {metrics.slug_precision:.2%}",
        f"Slug recall: {metrics.slug_recall:.2%}",
        f"Generated titles: {metrics.generated_title_count}",
        f"Existing titles: {metrics.existing_title_count}",
        f"Title overlap: {metrics.overlap_title_count}",
        f"Title precision: {metrics.title_precision:.2%}",
        f"Title recall: {metrics.title_recall:.2%}",
        f"Generated description coverage: {metrics.generated_description_coverage:.2%}",
        f"Existing description coverage: {metrics.existing_description_coverage:.2%}",
        f"Section similarity: {metrics.section_similarity:.2%}",
    ]
    if report.generated_only_titles:
        lines.extend(
            [
                "Generated-only titles:" if show_all_diffs else "Sample generated-only titles:",
                *[
                    f"- {title}"
                    for title in (
                        report.generated_only_titles
                        if show_all_diffs
                        else report.generated_only_titles[:5]
                    )
                ],
            ]
        )
    if report.existing_only_titles:
        lines.extend(
            [
                "Existing-only titles:" if show_all_diffs else "Sample existing-only titles:",
                *[
                    f"- {title}"
                    for title in (
                        report.existing_only_titles
                        if show_all_diffs
                        else report.existing_only_titles[:5]
                    )
                ],
            ]
        )
    if show_markdown:
        lines.extend(
            [
                "",
                "Generated Markdown:",
                report.generated_result.llms_txt_markdown,
                "",
                "Existing Markdown:",
                report.existing_markdown,
            ]
        )

    return "\n".join(lines)


def format_eval_error(root_url: str, error: Exception) -> str:
    """Render a compact error report for one evaluation target."""

    return "\n".join(
        [
            f"Root URL: {root_url}",
            "Status: ERROR",
            f"Error: {error}",
        ]
    )


def load_eval_sites(sites_file: Path = DEFAULT_SITES_FILE) -> list[str]:
    """Load the checked-in list of evaluation site URLs."""

    sites: list[str] = []
    for raw_line in sites_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        sites.append(normalize_url(line))

    return sites


def _candidate_llms_txt_urls(root_url: str) -> list[str]:
    split_result = urlsplit(root_url)
    normalized_path = split_result.path.rstrip("/")
    domain_root_url = urljoin(root_url, "/llms.txt")

    if not normalized_path:
        return [domain_root_url]

    path_local_url = f"{root_url.rstrip('/')}/llms.txt"
    if path_local_url == domain_root_url:
        return [domain_root_url]

    return [path_local_url, domain_root_url]


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None


def _normalize_title(title: str) -> str:
    normalized_title = _unescape_markdown_text(title).casefold()
    normalized_title = normalized_title.replace("–", "-").replace("—", "-")
    normalized_title = re.sub(r"\s[-|:]\s", " | ", normalized_title)
    normalized_title = re.sub(r"[^a-z0-9|]+", " ", normalized_title)
    normalized_title = " ".join(normalized_title.split())

    if " | " in normalized_title:
        normalized_title = normalized_title.split(" | ", 1)[0].strip()
    return normalized_title


def _normalize_url_slug(url: str) -> str:
    split_result = urlsplit(url)
    path = split_result.path.casefold().strip("/")
    if not path:
        return "/"

    normalized_path = re.sub(r"/index\.(html|htm|md|txt)$", "", path)
    normalized_path = re.sub(r"\.(html|htm|md|txt)$", "", normalized_path)
    normalized_path = re.sub(r"/+", "/", normalized_path).strip("/")
    return normalized_path or "/"


def _unescape_markdown_text(text: str) -> str:
    return re.sub(r"\\([\\`*_{}\[\]()#+\-.!&|:])", r"\1", text)


def _diff_titles(
    generated_entries: list[EvalEntry],
    existing_entries: list[EvalEntry],
) -> tuple[list[str], list[str]]:
    generated_by_title = {_normalize_title(entry.title): entry.title for entry in generated_entries}
    existing_by_title = {_normalize_title(entry.title): entry.title for entry in existing_entries}

    generated_only = sorted(
        title
        for normalized_title, title in generated_by_title.items()
        if normalized_title not in existing_by_title
    )
    existing_only = sorted(
        title
        for normalized_title, title in existing_by_title.items()
        if normalized_title not in generated_by_title
    )
    return generated_only, existing_only


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _description_coverage(entries: list[EvalEntry]) -> float:
    if not entries:
        return 0.0

    described_entries = sum(1 for entry in entries if entry.description)
    return described_entries / len(entries)


def _section_similarity(generated_entries: list[EvalEntry], existing_entries: list[EvalEntry]) -> float:
    generated_sections = {entry.section for entry in generated_entries}
    existing_sections = {entry.section for entry in existing_entries}
    union = generated_sections | existing_sections
    if not union:
        return 0.0

    return len(generated_sections & existing_sections) / len(union)


def main(argv: list[str] | None = None) -> int:
    """Run the evaluation harness as a small CLI."""

    args = argv if argv is not None else __import__("sys").argv[1:]
    show_markdown = "--show-markdown" in args
    show_all_diffs = "--show-all-diffs" in args
    if any(arg not in {"--show-markdown", "--show-all-diffs"} for arg in args):
        print(
            "Usage: python -m tests.evaluation.run_eval "
            "[--show-markdown] [--show-all-diffs]"
        )
        return 1

    for index, site_url in enumerate(load_eval_sites()):
        if index:
            print("\n" + ("-" * 48) + "\n")
        try:
            report = asyncio.run(evaluate_site(site_url))
        except Exception as error:
            print(format_eval_error(site_url, error))
            continue

        print(
            format_eval_report(
                report,
                show_markdown=show_markdown,
                show_all_diffs=show_all_diffs,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
