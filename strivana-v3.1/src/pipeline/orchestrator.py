"""Pipeline orchestrator for Strivana v3.1."""

import asyncio
import logging
import os
from typing import Any

from src.crawlers.parallel_waterfall import crawl_parallel
from src.extractors.identity_extractor import extract_identity
from src.output.ghl_pusher import push_to_ghl
from src.scoring.heuristic_scorer import score_lead
from src.scoring.intent_detector import detect_intent_signals

logger = logging.getLogger(__name__)


async def _process_url(
    url: str, ghl_token: str, location_id: str, semaphore: asyncio.Semaphore
) -> dict[str, Any]:
    """Process a single URL through the full pipeline.

    Steps:
    1. Crawl URL
    2. Extract identity
    3. Detect intent
    4. Score leads
    5. Push to GHL

    Args:
        url: URL to process.
        ghl_token: GoHighLevel API token.
        location_id: GHL location ID.
        semaphore: Async semaphore for concurrency control.

    Returns:
        List of push results for leads from this URL.
    """
    async with semaphore:
        results = []
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]

        logger.info(f"Processing URL: {url}")

        try:
            # Step 1: Crawl
            logger.debug(f"Crawling {url}")
            crawl_result = await crawl_parallel(url, timeout=30)

            if not crawl_result.get("success"):
                logger.error(f"Crawl failed for {url}")
                return {"url": url, "success": False, "error": "Crawl failed", "leads_processed": 0}

            html = crawl_result.get("html", "")
            source = crawl_result.get("source", "unknown")
            logger.info(f"Crawl successful for {url} (source: {source})")

            # Step 2: Extract identity
            logger.debug(f"Extracting identities from {domain}")
            leads = extract_identity(html, domain)

            if not leads:
                logger.warning(f"No identities extracted from {url}")
                return {"url": url, "success": True, "error": "", "leads_processed": 0}

            logger.info(f"Extracted {len(leads)} leads from {url}")

            # Step 3 & 4: Detect intent and score each lead
            scored_leads = []
            for lead in leads:
                # Extract text for intent detection
                page_text = html[:5000] if html else ""  # Limit text length

                # Score lead (includes intent detection internally)
                scored_lead = score_lead(lead, page_text)
                scored_leads.append(scored_lead)
                logger.info(
                    f"Lead scored: {scored_lead.name or 'Unknown'} - "
                    f"score={scored_lead.score}, confidence={scored_lead.confidence}"
                )

            # Step 5: Push to GHL
            push_results = []
            for lead in scored_leads:
                push_result = push_to_ghl(lead, ghl_token, location_id)
                push_results.append(push_result)
                results.append({
                    "lead_name": lead.name,
                    "lead_email": lead.email,
                    "score": lead.score,
                    "push_success": push_result.get("success", False),
                })

            total_success = sum(1 for r in push_results if r.get("success"))
            logger.info(
                f"Pipeline complete for {url}: {len(leads)} leads, "
                f"{total_success}/{len(leads)} pushed successfully"
            )

            return {
                "url": url,
                "success": True,
                "error": "",
                "leads_processed": len(leads),
                "leads_pushed": total_success,
                "results": results,
            }

        except Exception as e:
            logger.exception(f"Error processing {url}: {e}")
            return {"url": url, "success": False, "error": str(e), "leads_processed": 0}


async def run_pipeline(
    urls: list[str], ghl_token: str, location_id: str, max_concurrent: int = 10
) -> list[dict[str, Any]]:
    """Run the full Strivana pipeline on a list of URLs.

    Processes URLs concurrently with semaphore-based concurrency control.
    Each URL goes through: crawl → extract → detect intent → score → push.

    Args:
        urls: List of URLs to process.
        ghl_token: GoHighLevel API token.
        location_id: GHL location ID.
        max_concurrent: Maximum concurrent URL processing (default 10).

    Returns:
        List of processing results for each URL.
    """
    logger.info(f"Starting pipeline for {len(urls)} URLs (max concurrent: {max_concurrent})")

    semaphore = asyncio.Semaphore(max_concurrent)

    # Create tasks for all URLs
    tasks = [
        _process_url(url, ghl_token, location_id, semaphore)
        for url in urls
    ]

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process any exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.exception(f"Task exception for URL {urls[i]}: {result}")
            processed_results.append({
                "url": urls[i],
                "success": False,
                "error": str(result),
                "leads_processed": 0,
            })
        else:
            processed_results.append(result)

    # Summary
    total_leads = sum(r.get("leads_processed", 0) for r in processed_results)
    total_pushed = sum(r.get("leads_pushed", 0) for r in processed_results)
    successful_urls = sum(1 for r in processed_results if r.get("success"))

    logger.info(
        f"Pipeline complete: {successful_urls}/{len(urls)} URLs successful, "
        f"{total_leads} leads extracted, {total_pushed} leads pushed"
    )

    return processed_results


async def main() -> None:
    """Main entry point for running the pipeline."""
    # Load configuration from environment
    ghl_token = os.getenv("GHL_TOKEN", "")
    location_id = os.getenv("LOCATION_ID", "")

    if not ghl_token or not location_id:
        logger.error("Missing GHL_TOKEN or LOCATION_ID environment variables")
        return

    # Load target URLs from config or use defaults
    targets_file = os.getenv("TARGETS_FILE", "config/targets.txt")
    urls = []

    try:
        with open(targets_file, "r") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        logger.warning(f"Targets file not found: {targets_file}, using default URLs")
        urls = [
            "https://example.com",
            "https://example.org",
        ]

    logger.info(f"Loaded {len(urls)} target URLs")

    # Run pipeline
    results = await run_pipeline(urls, ghl_token, location_id)

    # Output summary
    print("\n=== Pipeline Results ===")
    for result in results:
        status = "✓" if result.get("success") else "✗"
        print(f"{status} {result.get('url')}: {result.get('leads_processed', 0)} leads")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())
