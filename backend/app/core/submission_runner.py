"""Run Playwright coroutines on the FastAPI event loop from APScheduler threads."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_main_loop: asyncio.AbstractEventLoop | None = None

# Playwright on Render can take several minutes (login + fill + submit).
DEFAULT_TIMEOUT_SEC = 600


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def run_async(coro: Coroutine[Any, Any, T], *, timeout: float = DEFAULT_TIMEOUT_SEC) -> T:
    """Execute an async submission on the main loop when available."""
    loop = _main_loop
    if loop is not None and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            return future.result(timeout=timeout)
        except Exception:
            future.cancel()
            raise
    logger.debug("No running main loop; falling back to asyncio.run()")
    return asyncio.run(coro)
