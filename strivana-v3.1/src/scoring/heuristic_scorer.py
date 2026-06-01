"""Heuristic scorer for lead qualification."""

import logging

from src.models.lead import Lead
from src.router.model_swipe import ModelSwipeRouter
from src.scoring.intent_detector import detect_intent_signals

logger = logging.getLogger(__name__)


def score_lead(lead: Lead, page_text: str = "") -> Lead:
    """Score a lead using heuristic rules with LLM fallback.

    Adds points for:
    - Decision maker title (+40)
    - Valid email (+30)
    - Valid phone (+20)
    - Company size >10 (+10)
    - Intent signals (variable)

    Caps score at 100. Sets confidence based on score thresholds.
    Routes to LLM fallback if confidence < 0.3.

    Args:
        lead: Lead object to score.
        page_text: Optional page text for intent detection.

    Returns:
        Updated Lead object with score and confidence.
    """
    router = ModelSwipeRouter()
    score = 0

    # Check decision maker title (+40)
    if router._is_decision_maker(lead.title):
        score += 40
        logger.debug(f"Decision maker title detected for {lead.name}: +40 points")

    # Check valid email (+30)
    if router._is_valid_email(lead.email):
        score += 30
        logger.debug(f"Valid email detected for {lead.name}: +30 points")

    # Check valid phone (+20)
    if router._validate_phone(lead.phone):
        score += 20
        logger.debug(f"Valid phone detected for {lead.name}: +20 points")

    # Company size check (+10) - stub implementation
    # In production, this would check actual company size data
    if lead.company:
        # Simple heuristic: if company name suggests larger org
        large_company_indicators = ["inc", "corp", "ltd", "llc", "group", "international", "global"]
        if any(indicator in lead.company.lower() for indicator in large_company_indicators):
            score += 10
            logger.debug(f"Large company indicator for {lead.company}: +10 points")

    # Add intent score from page text
    if page_text:
        intent_result = detect_intent_signals(page_text)
        intent_score = intent_result.get("intent_score", 0)
        signals = intent_result.get("signals", [])

        # Add intent score (scaled to max 20 points for base scoring)
        if intent_score > 0:
            intent_points = min(intent_score // 5, 20)  # Max 20 points from intent
            score += intent_points
            lead.intent_score = intent_score
            lead.signals = signals
            logger.debug(f"Intent signals detected: {len(signals)} signals, +{intent_points} points")

    # Cap at 100
    lead.score = min(score, 100)

    # Set confidence based on score thresholds
    if lead.score >= 70:
        lead.confidence = 0.9
    elif lead.score >= 50:
        lead.confidence = 0.6
    elif lead.score >= 30:
        lead.confidence = 0.4
    else:
        lead.confidence = 0.2

    # Check if LLM fallback is needed
    if lead.confidence < 0.3:
        logger.warning(
            f"Low confidence ({lead.confidence}) for lead {lead.name or lead.domain}, "
            f"routing to LLM fallback"
        )
        # Route to ModelSwipeRouter for LLM fallback
        context = {"confidence": lead.confidence, "lead_data": lead.model_dump()}
        model_name, llm_method = router.route("score_lead", context)

        if model_name == "deepseek-chat":
            # Call LLM fallback method (returns safe defaults)
            fallback_result = llm_method(context["lead_data"])
            lead.score = fallback_result.get("score", 10)
            lead.confidence = fallback_result.get("confidence", 0.1)
            logger.info(f"LLM fallback applied: score={lead.score}, confidence={lead.confidence}")

    logger.info(
        f"Lead scored: {lead.name or 'Unknown'} ({lead.domain}) - "
        f"score={lead.score}, confidence={lead.confidence}"
    )
    return lead
