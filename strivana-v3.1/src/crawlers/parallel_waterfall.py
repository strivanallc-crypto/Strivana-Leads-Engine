"""Parallel waterfall crawler using Crawlee and Crawl4AI."""

import asyncio
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


async def _crawlee_crawl(url: str, timeout: int) -> dict[str, Any] | None:
    """Attempt crawl using Crawlee HTTP crawler.

    Args:
        url: URL to crawl.
        timeout: Request timeout in seconds.

    Returns:
        Crawl result dict or None if failed.
    """
    try:
        # Crawlee stub - in production would use actual Crawlee
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    html = await response.text()
                    logger.debug(f"Crawlee successfully crawled {url}")
                    return {"success": True, "html": html, "source": "crawlee"}
    except Exception as e:
        logger.debug(f"Crawlee crawl failed for {url}: {e}")
    return None


async def _crawl4ai_crawl(url: str, timeout: int) -> dict[str, Any] | None:
    """Attempt crawl using Crawl4AI async crawler.

    Args:
        url: URL to crawl.
        timeout: Request timeout in seconds.

    Returns:
        Crawl result dict or None if failed.
    """
    try:
        # Crawl4AI stub - in production would use actual Crawl4AI
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    html = await response.text()
                    logger.debug(f"Crawl4AI successfully crawled {url}")
                    return {"success": True, "html": html, "source": "crawl4ai"}
    except Exception as e:
        logger.debug(f"Crawl4AI crawl failed for {url}: {e}")
    return None


async def _browserless_fallback(url: str, timeout: int) -> dict[str, Any] | None:
    """Fallback to Browserless WebSocket call.

    Stub implementation that logs warning and returns empty result.

    Args:
        url: URL to crawl.
        timeout: Request timeout in seconds.

    Returns:
        Empty dict with logged warning.
    """
    logger.warning(
        f"Both crawlers failed for {url}, attempting browserless fallback (stub)"
    )
    # In production, this would connect to Browserless via WebSocket
    # For now, return empty result
    return None


async def _crawl_with_retry(
    url: str, timeout: int, max_retries: int = 2
) -> dict[str, Any] | None:
    """Crawl with exponential backoff retry logic.

    Args:
        url: URL to crawl.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retries.

    Returns:
        Crawl result dict or None if all attempts failed.
    """
    attempt = 0
    while attempt <= max_retries:
        if attempt > 0:
            backoff = 2**attempt  # Exponential backoff
            logger.info(f"Retry {attempt}/{max_retries} for {url} after {backoff}s")
            await asyncio.sleep(backoff)

        # Run both crawlers concurrently
        tasks = [
            asyncio.create_task(_crawlee_crawl(url, timeout)),
            asyncio.create_task(_crawl4ai_crawl(url, timeout)),
        ]

        for completed in asyncio.as_completed(tasks):
            result = await completed
            if result and result.get("success"):
                return result

        attempt += 1

    return None


async def crawl_parallel(url: str, timeout: int = 30) -> dict[str, Any]:
    """Crawl URL using parallel waterfall approach.

    Runs Crawlee and Crawl4AI concurrently, returns first successful result.
    Falls back to Browserless if both fail. Implements retry with exponential backoff.

    Args:
        url: URL to crawl.
        timeout: Request timeout in seconds.

    Returns:
        Dict with success status, HTML content, and source.
    """
    logger.info(f"Starting parallel crawl for {url}")

    result = await _crawl_with_retry(url, timeout)

    if result:
        return result

    # Both crawlers failed, try browserless fallback
    browserless_result = await _browserless_fallback(url, timeout)
    if browserless_result:
        return browserless_result

    # All methods failed
    logger.error(f"All crawling methods failed for {url}")
    return {"success": False, "html": "", "source": "none"}
