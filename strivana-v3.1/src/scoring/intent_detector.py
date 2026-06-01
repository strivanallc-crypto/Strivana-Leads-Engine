"""Intent detection for identifying lead signals."""

import logging
import re
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# Intent signal patterns with point values
INTENT_PATTERNS: dict[str, tuple[re.Pattern, int]] = {
    # Hiring signals (15-25 points)
    "hiring_job_posting": (re.compile(r"\b(hiring|we'?re hiring|join our team|career opportunity|job opening|now hiring)\b", re.IGNORECASE), 20),
    "hiring_expansion": (re.compile(r"\b(expanding team|growing team|team growth|headcount increase)\b", re.IGNORECASE), 25),

    # Funding signals (15-25 points)
    "funding_series": (re.compile(r"\b(series [a-z]|seed funding|venture capital|fundraising|raised \d+[mk]b?|investment round)\b", re.IGNORECASE), 25),
    "funding_investor": (re.compile(r"\b(investor|backed by|funded by|capital injection|financial backing)\b", re.IGNORECASE), 20),

    # Tech migration signals (15-25 points)
    "tech_migration": (re.compile(r"\b(migrating to|moving to|adopting new|technology upgrade|digital transformation|modernization)\b", re.IGNORECASE), 20),
    "tech_implementation": (re.compile(r"\b(implementing new|deploying new|rolling out|integration project|system upgrade)\b", re.IGNORECASE), 15),

    # Recent activity signals (15-25 points)
    "recent_launch": (re.compile(r"\b(newly launched|just announced|recently released|fresh off|brand new)\b", re.IGNORECASE), 20),
    "recent_partnership": (re.compile(r"\b(new partnership|strategic alliance|collaboration announced|partnered with)\b", re.IGNORECASE), 25),
}

# Date patterns for recent activity detection
DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2})\s*(days?|weeks?)?\s*ago\b", re.IGNORECASE),
    re.compile(r"\b(this|last)\s*(week|month)\b", re.IGNORECASE),
    re.compile(r"\b(recently|lately|newly|just)\b", re.IGNORECASE),
]


def _check_recent_activity(text: str) -> bool:
    """Check if text indicates recent activity (<30 days).

    Args:
        text: Text content to analyze.

    Returns:
        True if recent activity is detected.
    """
    # Check explicit date patterns
    for pattern in DATE_PATTERNS:
        if pattern.search(text):
            return True

    # Check for specific recent dates (within last 30 days)
    try:
        today = datetime.now()
        thirty_days_ago = today - timedelta(days=30)

        # Look for date formats like "January 15, 2024" or "2024-01-15"
        date_formats = ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"]
        for fmt in date_formats:
            for match in re.finditer(r'\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|\w+\s+\d{1,2},?\s+\d{4}', text):
                try:
                    date_str = match.group()
                    parsed_date = datetime.strptime(date_str, fmt)
                    if parsed_date >= thirty_days_ago:
                        return True
                except ValueError:
                    continue
    except Exception as e:
        logger.debug(f"Error checking recent activity: {e}")

    return False


def detect_intent_signals(text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Detect intent signals from text content.

    Matches regex patterns for:
    - Hiring/job posting activity
    - Funding/series announcements
    - Technology migration/upgrade
    - Recent activity (<30 days)

    Args:
        text: Text content to analyze.
        metadata: Optional metadata dictionary (not used currently).

    Returns:
        Dictionary with intent_score (0-100) and list of signals.
    """
    signals: list[str] = []
    intent_score = 0

    if not text:
        return {"intent_score": 0, "signals": []}

    # Match intent patterns
    for signal_name, (pattern, points) in INTENT_PATTERNS.items():
        if pattern.search(text):
            signals.append(signal_name)
            intent_score += points
            logger.debug(f"Detected intent signal: {signal_name} (+{points} points)")

    # Check for recent activity
    if _check_recent_activity(text):
        signals.append("recent_activity")
        intent_score += 15
        logger.debug("Detected recent activity signal (+15 points)")

    # Cap score at 100
    intent_score = min(intent_score, 100)

    logger.info(f"Intent detection complete: score={intent_score}, signals={len(signals)}")
    return {"intent_score": intent_score, "signals": signals}
