"""Model swipe router for heuristic-first routing with LLM fallback."""

import logging
import re
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class ModelSwipeRouter:
    """Routes tasks to heuristic or LLM based on confidence threshold.

    Implements identity-first extraction with model swipe logic:
    - High confidence (>=0.3): Use fast heuristic methods
    - Low confidence (<0.3): Fall back to LLM (deepseek-chat)
    """

    DECISION_MAKER_PATTERNS = re.compile(
        r"\b(ceo|chief\s*executive|cfo|chief\s*financial|cto|chief\s*technical|"
        r"coo|chief\s*operating|founder|co-founder|cofounder|president|"
        r"vp|vice\s*president|director|partner|managing\s*partner|"
        r"head\s*of|chief\s*.*officer)\b",
        re.IGNORECASE,
    )

    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    def __init__(self) -> None:
        """Initialize the router with bound methods."""
        self._heuristic_methods: dict[str, Callable] = {
            "score_lead": self._heuristic_score,
            "extract_identity": self._heuristic_extract,
            "detect_intent": self._heuristic_intent,
        }
        self._llm_methods: dict[str, Callable] = {
            "score_lead": self._llm_score_fallback,
            "extract_identity": self._llm_extract_fallback,
            "detect_intent": self._llm_intent_fallback,
        }

    def route(self, task: str, context: dict[str, Any]) -> tuple[str, Callable]:
        """Route a task to heuristic or LLM based on confidence.

        Args:
            task: Task name ("score_lead", "extract_identity", "detect_intent").
            context: Context dictionary containing confidence and other metadata.

        Returns:
            Tuple of (model_name, bound_method).
        """
        confidence = context.get("confidence", 1.0)

        if confidence >= 0.3:
            method = self._heuristic_methods.get(task)
            if method:
                logger.debug(f"Routing '{task}' to heuristic (confidence={confidence})")
                return "heuristic", method
            else:
                logger.warning(f"Unknown task '{task}', defaulting to heuristic")
                return "heuristic", lambda *args, **kwargs: {}

        else:
            method = self._llm_methods.get(task)
            if method:
                logger.info(f"Routing '{task}' to deepseek-chat (confidence={confidence})")
                return "deepseek-chat", method
            else:
                logger.warning(f"Unknown task '{task}', defaulting to LLM fallback")
                return "deepseek-chat", lambda *args, **kwargs: {}

    def _is_decision_maker(self, title: str) -> bool:
        """Check if title indicates decision-making authority.

        Args:
            title: Job title string.

        Returns:
            True if title matches decision-maker patterns.
        """
        if not title:
            return False
        return bool(self.DECISION_MAKER_PATTERNS.search(title))

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format and length.

        Args:
            email: Email address to validate.

        Returns:
            True if email is valid.
        """
        if not email or len(email) > 254:
            return False
        return bool(self.EMAIL_PATTERN.match(email))

    def _validate_phone(self, phone: str) -> bool:
        """Validate phone number format.

        Strips non-digits and checks for 10 digits with valid area code.

        Args:
            phone: Phone number string.

        Returns:
            True if phone is valid.
        """
        if not phone:
            return False
        digits = re.sub(r"\D", "", phone)
        if len(digits) != 10:
            return False
        area_code = int(digits[:3])
        # Area code cannot start with 0 or 1
        if area_code < 200:
            return False
        return True

    def _heuristic_score(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """Heuristic scoring implementation.

        Args:
            lead_data: Dictionary containing lead information.

        Returns:
            Scored lead data with score and confidence.
        """
        score = 0
        title = lead_data.get("title", "")
        email = lead_data.get("email", "")
        phone = lead_data.get("phone", "")

        if self._is_decision_maker(title):
            score += 40
        if self._is_valid_email(email):
            score += 30
        if self._validate_phone(phone):
            score += 20

        # Cap at 100
        score = min(score, 100)

        # Set confidence based on score thresholds
        if score >= 70:
            confidence = 0.9
        elif score >= 50:
            confidence = 0.6
        elif score >= 30:
            confidence = 0.4
        else:
            confidence = 0.2

        lead_data["score"] = score
        lead_data["confidence"] = confidence
        return lead_data

    def _heuristic_extract(self, html: str, domain: str) -> list[dict[str, Any]]:
        """Heuristic identity extraction stub.

        Actual extraction is done by extractors.identity_extractor.
        This is a fallback placeholder.

        Args:
            html: HTML content.
            domain: Domain name.

        Returns:
            List of extracted identity dictionaries.
        """
        logger.warning("Heuristic extract called - should use identity_extractor instead")
        return []

    def _heuristic_intent(self, text: str, metadata: dict | None = None) -> dict[str, Any]:
        """Heuristic intent detection stub.

        Actual detection is done by scoring.intent_detector.
        This is a fallback placeholder.

        Args:
            text: Text content to analyze.
            metadata: Optional metadata dictionary.

        Returns:
            Intent detection result.
        """
        logger.warning("Heuristic intent called - should use intent_detector instead")
        return {"intent_score": 0, "signals": []}

    def _llm_score_fallback(self, lead_data: dict[str, Any]) -> dict[str, Any]:
        """LLM fallback for scoring when confidence is low.

        Logs warning and returns safe defaults without actual API call.

        Args:
            lead_data: Dictionary containing lead information.

        Returns:
            Lead data with default score and low confidence.
        """
        logger.warning(
            f"LLM fallback triggered for scoring: {lead_data.get('name', 'unknown')}"
        )
        # Safe defaults
        lead_data["score"] = 10
        lead_data["confidence"] = 0.1
        return lead_data

    def _llm_extract_fallback(self, html: str, domain: str) -> list[dict[str, Any]]:
        """LLM fallback for identity extraction when confidence is low.

        Logs warning and returns empty result.

        Args:
            html: HTML content.
            domain: Domain name.

        Returns:
            Empty list (safe default).
        """
        logger.warning(f"LLM fallback triggered for extraction on domain: {domain}")
        return []

    def _llm_intent_fallback(self, text: str, metadata: dict | None = None) -> dict[str, Any]:
        """LLM fallback for intent detection when confidence is low.

        Logs warning and returns zero intent.

        Args:
            text: Text content to analyze.
            metadata: Optional metadata dictionary.

        Returns:
            Zero intent result (safe default).
        """
        logger.warning("LLM fallback triggered for intent detection")
        return {"intent_score": 0, "signals": []}
