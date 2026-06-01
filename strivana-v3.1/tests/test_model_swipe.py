"""Tests for model swipe router."""

import pytest

from src.router.model_swipe import ModelSwipeRouter


class TestModelSwipeRouter:
    """Test model swipe routing logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.router = ModelSwipeRouter()

    def test_route_high_confidence_to_heuristic(self):
        """Test routing high confidence tasks to heuristic."""
        context = {"confidence": 0.8}
        model_name, method = self.router.route("score_lead", context)

        assert model_name == "heuristic"
        assert callable(method)

    def test_route_low_confidence_to_llm(self):
        """Test routing low confidence tasks to LLM fallback."""
        context = {"confidence": 0.1}
        model_name, method = self.router.route("score_lead", context)

        assert model_name == "deepseek-chat"
        assert callable(method)

    def test_route_default_confidence(self):
        """Test routing with default confidence (should be heuristic)."""
        context = {}
        model_name, method = self.router.route("score_lead", context)

        assert model_name == "heuristic"

    def test_route_threshold_boundary(self):
        """Test routing at exact threshold boundary (0.3)."""
        context = {"confidence": 0.3}
        model_name, method = self.router.route("score_lead", context)

        assert model_name == "heuristic"

        context = {"confidence": 0.299}
        model_name, method = self.router.route("score_lead", context)

        assert model_name == "deepseek-chat"

    def test_route_all_tasks(self):
        """Test routing all supported tasks."""
        tasks = ["score_lead", "extract_identity", "detect_intent"]
        context = {"confidence": 0.5}

        for task in tasks:
            model_name, method = self.router.route(task, context)
            assert model_name == "heuristic"
            assert callable(method)

    def test_route_unknown_task(self):
        """Test routing unknown task (should default gracefully)."""
        context = {"confidence": 0.5}
        model_name, method = self.router.route("unknown_task", context)

        # Should still return a callable
        assert callable(method)


class TestDecisionMakerDetection:
    """Test decision maker title detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.router = ModelSwipeRouter()

    def test_detect_ceo(self):
        """Test detecting CEO title."""
        assert self.router._is_decision_maker("CEO") is True
        assert self.router._is_decision_maker("Chief Executive Officer") is True

    def test_detect_founder(self):
        """Test detecting Founder title."""
        assert self.router._is_decision_maker("Founder") is True
        assert self.router._is_decision_maker("Co-Founder") is True
        assert self.router._is_decision_maker("Cofounder") is True

    def test_detect_vp(self):
        """Test detecting VP title."""
        assert self.router._is_decision_maker("VP of Engineering") is True
        assert self.router._is_decision_maker("Vice President") is True

    def test_detect_director(self):
        """Test detecting Director title."""
        assert self.router._is_decision_maker("Director of Sales") is True
        assert self.router._is_decision_maker("Managing Director") is True

    def test_detect_partner(self):
        """Test detecting Partner title."""
        assert self.router._is_decision_maker("Partner") is True
        assert self.router._is_decision_maker("Managing Partner") is True

    def test_non_decision_maker(self):
        """Test non-decision-maker titles."""
        assert self.router._is_decision_maker("Software Engineer") is False
        assert self.router._is_decision_maker("Manager") is False
        assert self.router._is_decision_maker("Analyst") is False
        assert self.router._is_decision_maker("") is False
        assert self.router._is_decision_maker(None) is False

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        assert self.router._is_decision_maker("ceo") is True
        assert self.router._is_decision_maker("Ceo") is True
        assert self.router._is_decision_maker("FOUNDer") is True


class TestEmailValidation:
    """Test email validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.router = ModelSwipeRouter()

    def test_valid_emails(self):
        """Test valid email addresses."""
        assert self.router._is_valid_email("john@example.com") is True
        assert self.router._is_valid_email("jane.doe@company.co.uk") is True
        assert self.router._is_valid_email("user+tag@example.org") is True

    def test_invalid_emails(self):
        """Test invalid email addresses."""
        assert self.router._is_valid_email("invalid") is False
        assert self.router._is_valid_email("@example.com") is False
        assert self.router._is_valid_email("john@") is False
        assert self.router._is_valid_email("") is False

    def test_email_length_limit(self):
        """Test email length limit (254 characters)."""
        long_email = "a" * 250 + "@example.com"
        assert self.router._is_valid_email(long_email) is False


class TestPhoneValidation:
    """Test phone number validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.router = ModelSwipeRouter()

    def test_valid_phones(self):
        """Test valid phone numbers."""
        assert self.router._validate_phone("5551234567") is True
        assert self.router._validate_phone("(555) 123-4567") is True
        assert self.router._validate_phone("555-123-4567") is True
        # Note: +1 international format results in 11 digits, so we test US format without country code
        assert self.router._validate_phone("555 123 4567") is True

    def test_invalid_phones(self):
        """Test invalid phone numbers."""
        assert self.router._validate_phone("123456789") is False  # 9 digits
        assert self.router._validate_phone("12345678901") is False  # 11 digits
        assert self.router._validate_phone("") is False
        assert self.router._validate_phone(None) is False

    def test_invalid_area_code(self):
        """Test invalid area codes (cannot start with 0 or 1)."""
        assert self.router._validate_phone("0551234567") is False
        assert self.router._validate_phone("1551234567") is False

    def test_valid_area_codes(self):
        """Test valid area codes (2-9)."""
        assert self.router._validate_phone("2551234567") is True
        assert self.router._validate_phone("9551234567") is True


class TestHeuristicScoring:
    """Test heuristic scoring implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.router = ModelSwipeRouter()

    def test_score_decision_maker(self):
        """Test scoring with decision maker title."""
        lead_data = {
            "name": "John Smith",
            "title": "CEO",
            "email": "",
            "phone": "",
        }
        result = self.router._heuristic_score(lead_data)

        assert result["score"] == 40  # Decision maker only
        assert result["confidence"] == 0.4

    def test_score_with_email(self):
        """Test scoring with valid email."""
        lead_data = {
            "name": "Jane Doe",
            "title": "",
            "email": "jane@example.com",
            "phone": "",
        }
        result = self.router._heuristic_score(lead_data)

        assert result["score"] == 30  # Email only
        assert result["confidence"] == 0.4

    def test_score_with_phone(self):
        """Test scoring with valid phone."""
        lead_data = {
            "name": "Bob Wilson",
            "title": "",
            "email": "",
            "phone": "5551234567",
        }
        result = self.router._heuristic_score(lead_data)

        assert result["score"] == 20  # Phone only
        assert result["confidence"] == 0.2

    def test_score_complete_lead(self):
        """Test scoring with all fields."""
        lead_data = {
            "name": "Alice Brown",
            "title": "VP of Sales",
            "email": "alice@company.com",
            "phone": "5559876543",
        }
        result = self.router._heuristic_score(lead_data)

        # Decision maker (40) + Email (30) + Phone (20) = 90
        assert result["score"] == 90
        assert result["confidence"] == 0.9

    def test_score_cap_at_100(self):
        """Test that score caps at 100."""
        lead_data = {
            "name": "Max Score",
            "title": "CEO",
            "email": "max@example.com",
            "phone": "5551112222",
        }
        result = self.router._heuristic_score(lead_data)

        assert result["score"] <= 100


class TestLlmFallback:
    """Test LLM fallback methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.router = ModelSwipeRouter()

    def test_llm_score_fallback(self):
        """Test LLM score fallback returns safe defaults."""
        lead_data = {"name": "Test User"}
        result = self.router._llm_score_fallback(lead_data)

        assert result["score"] == 10
        assert result["confidence"] == 0.1

    def test_llm_extract_fallback(self):
        """Test LLM extract fallback returns empty list."""
        result = self.router._llm_extract_fallback("<html></html>", "example.com")

        assert result == []

    def test_llm_intent_fallback(self):
        """Test LLM intent fallback returns zero intent."""
        result = self.router._llm_intent_fallback("Some text")

        assert result["intent_score"] == 0
        assert result["signals"] == []
