"""Abstract base collector with retry logic, timeout, and structured logging."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import logging

from config.settings import settings


# Bridge loguru to tenacity's standard-logging callback
_std_logger = logging.getLogger("tenacity.collector")


class BaseCollector(ABC):
    """Base class for all data collectors.

    Provides:
    - Async collect() with top-level error handling (never crashes)
    - Tenacity retry wrapper for flaky HTTP calls
    - Configurable timeout (default from settings.COLLECTOR_TIMEOUT)
    - Structured loguru logging
    """

    name: str = "base"
    timeout: int = settings.COLLECTOR_TIMEOUT  # seconds

    # Common browser-like headers for NSE scraping
    NSE_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.nseindia.com/",
    }

    async def safe_collect(self) -> Any:
        """Top-level wrapper — guarantees no exception escapes.

        Returns whatever _collect() returns, or the default fallback on any failure.
        """
        try:
            result = await asyncio.wait_for(
                self._collect(), timeout=self.timeout
            )
            logger.success(f"[{self.name}] Collection complete")
            return result
        except asyncio.TimeoutError:
            logger.error(f"[{self.name}] Timed out after {self.timeout}s")
            return self._default()
        except Exception as exc:
            logger.error(f"[{self.name}] Failed: {type(exc).__name__}: {exc}")
            return self._default()

    @abstractmethod
    async def _collect(self) -> Any:
        """Subclasses implement actual data collection here."""
        ...

    @abstractmethod
    def _default(self) -> Any:
        """Return empty/default data when collection fails."""
        ...

    @staticmethod
    def _retry(fn):
        """Decorator for retrying flaky calls (3 attempts, exponential backoff)."""
        return retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((Exception,)),
            before_sleep=before_sleep_log(_std_logger, logging.WARNING),
            reraise=True,
        )(fn)

    @staticmethod
    async def _run_sync(fn, *args, **kwargs):
        """Run a synchronous function in a thread pool (for yfinance etc.)."""
        import functools
        call = functools.partial(fn, *args, **kwargs)
        return await asyncio.get_event_loop().run_in_executor(None, call)
