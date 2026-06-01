"""GoHighLevel pusher for lead output."""

import logging
import subprocess
import time
from typing import Any

from src.models.lead import Lead

logger = logging.getLogger(__name__)


def _build_curl_command(
    payload: dict[str, Any], ghl_token: str, location_id: str
) -> list[str]:
    """Build curl command for GHL API.

    Args:
        payload: Contact payload dictionary.
        ghl_token: GoHighLevel API token.
        location_id: GHL location ID.

    Returns:
        List of command arguments for subprocess.run.
    """
    base_url = f"https://services.leadconnectorhq.com/contacts?locationId={location_id}"

    # Build JSON payload string manually to avoid json dependency issues
    json_parts = []
    for key, value in payload.items():
        if isinstance(value, str):
            json_parts.append(f'"{key}":"{value}"')
        elif isinstance(value, (int, float)):
            json_parts.append(f'"{key}":{value}')
        elif isinstance(value, list):
            json_parts.append(f'"{key}":["{",".join(str(v) for v in value)}"]')

    json_str = "{" + ",".join(json_parts) + "}"

    return [
        "curl",
        "-X", "POST",
        "-H", f"Authorization: Bearer {ghl_token}",
        "-H", "Content-Type: application/json",
        "-H", "Accept: application/json",
        "-d", json_str,
        base_url,
    ]


def _execute_curl_with_backoff(
    cmd: list[str], max_attempts: int = 3
) -> tuple[bool, str, str]:
    """Execute curl command with exponential backoff on failures.

    Args:
        cmd: Curl command as list of arguments.
        max_attempts: Maximum number of attempts.

    Returns:
        Tuple of (success, response, error).
    """
    last_error = ""
    response = ""

    for attempt in range(max_attempts):
        try:
            logger.debug(f"GHL push attempt {attempt + 1}/{max_attempts}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            response = result.stdout
            stderr = result.stderr

            if result.returncode == 0:
                # Check for rate limit or 5xx in response
                if "429" in response or "500" in response or "502" in response or "503" in response:
                    logger.warning(f"Rate limit or server error detected: {response}")
                    last_error = "Rate limit or server error"
                else:
                    logger.info("Successfully pushed to GHL")
                    return True, response, ""
            else:
                last_error = stderr or f"Curl exit code: {result.returncode}"
                logger.warning(f"Curl failed: {last_error}")

        except subprocess.TimeoutExpired:
            last_error = "Request timeout"
            logger.warning(f"GHL push timeout on attempt {attempt + 1}")
        except Exception as e:
            last_error = str(e)
            logger.error(f"GHL push error: {e}")

        # Exponential backoff before retry
        if attempt < max_attempts - 1:
            backoff = 2 ** attempt  # 1s, 2s, 4s
            logger.info(f"Retrying in {backoff}s...")
            time.sleep(backoff)

    return False, response, last_error


def push_to_ghl(lead: Lead, ghl_token: str, location_id: str) -> dict[str, Any]:
    """Push lead to GoHighLevel via API.

    Builds payload using lead.to_ghl_payload(), handles missing fields gracefully,
    and implements exponential backoff on rate limit or 5xx errors.

    Args:
        lead: Lead object to push.
        ghl_token: GoHighLevel API token.
        location_id: GHL location ID.

    Returns:
        Dict with success status, response, and error message.
    """
    # Build payload from lead
    payload = lead.to_ghl_payload()

    if not payload:
        logger.warning(f"Empty payload for lead {lead.domain}, skipping GHL push")
        return {"success": False, "response": "", "error": "Empty payload"}

    logger.info(
        f"Pushing lead to GHL: {lead.name or 'Unknown'} ({lead.domain}), "
        f"score={lead.score}, confidence={lead.confidence}"
    )

    # Build curl command
    cmd = _build_curl_command(payload, ghl_token, location_id)

    # Execute with backoff
    success, response, error = _execute_curl_with_backoff(cmd)

    result = {
        "success": success,
        "response": response[:500] if response else "",  # Truncate long responses
        "error": error,
    }

    if success:
        logger.info(f"GHL push successful for {lead.domain}")
    else:
        logger.error(f"GHL push failed for {lead.domain}: {error}")

    return result
