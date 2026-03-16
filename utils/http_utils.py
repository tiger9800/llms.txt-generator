"""Shared HTTP helpers used across crawler and pipeline services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

DEFAULT_USER_AGENT = "llmstxt-generator/1.0"


@asynccontextmanager
async def get_async_client(
    client: httpx.AsyncClient | None,
    *,
    follow_redirects: bool = True,
    timeout: float = 10.0,
) -> AsyncIterator[httpx.AsyncClient]:
    """Yield an injected async client or create a managed one when needed."""

    if client is not None:
        yield client
        return

    async with httpx.AsyncClient(
        follow_redirects=follow_redirects,
        timeout=timeout,
    ) as managed_client:
        yield managed_client
