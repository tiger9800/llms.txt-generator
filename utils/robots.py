"""Helpers for fetching and evaluating robots.txt policies."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from textwrap import dedent
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx

from utils.http_utils import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RobotsPolicy:
    """Simple fail-open wrapper around a parsed robots.txt policy."""

    parser: RobotFileParser | None
    user_agent: str = DEFAULT_USER_AGENT

    def allows(self, url: str) -> bool:
        """Return whether the configured user agent may fetch the URL."""

        if self.parser is None:
            return True

        if not self.parser.can_fetch(self.user_agent, url):
            return False

        user_agent_token = self.user_agent.split("/", 1)[0]
        if user_agent_token != self.user_agent:
            return self.parser.can_fetch(user_agent_token, url)

        return True


def _normalize_robots_lines(robots_text: str) -> list[str]:
    """Normalize robots.txt lines for RobotFileParser compatibility."""

    normalized_lines: list[str] = []
    for line in dedent(robots_text).strip().splitlines():
        stripped_line = line.strip()
        if stripped_line.lower().startswith("user-agent:"):
            _, raw_value = stripped_line.split(":", 1)
            normalized_value = raw_value.strip().split("/", 1)[0]
            normalized_lines.append(f"User-agent: {normalized_value}")
            continue

        normalized_lines.append(stripped_line)

    return normalized_lines


async def load_robots_policy(
    root_url: str,
    client: httpx.AsyncClient,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
) -> RobotsPolicy:
    """Fetch and parse robots.txt for the root URL, failing open on errors."""

    robots_url = urljoin(root_url, "/robots.txt")

    try:
        response = await client.get(robots_url, headers={"User-Agent": user_agent})
    except httpx.HTTPError:
        logger.warning("Failed to fetch robots.txt from %s; continuing with fail-open policy.", robots_url)
        return RobotsPolicy(parser=None, user_agent=user_agent)

    if response.status_code != 200:
        logger.info(
            "No usable robots.txt at %s (status %d); continuing with fail-open policy.",
            robots_url,
            response.status_code,
        )
        return RobotsPolicy(parser=None, user_agent=user_agent)

    try:
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(_normalize_robots_lines(response.text))
    except Exception:
        logger.warning("Failed to parse robots.txt from %s; continuing with fail-open policy.", robots_url)
        return RobotsPolicy(parser=None, user_agent=user_agent)

    return RobotsPolicy(parser=parser, user_agent=user_agent)
