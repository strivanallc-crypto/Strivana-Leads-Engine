"""Lead model definition for Strivana v3.1 pipeline."""

from typing import Optional
from pydantic import BaseModel, Field


class Lead(BaseModel):
    """Represents a lead extracted from web crawling with identity and scoring data.

    Attributes:
        name: Full name of the person (optional).
        title: Job title or role (optional).
        email: Email address (optional).
        phone: Phone number (optional).
        company: Company name (optional).
        domain: Domain name (required).
        score: Overall lead score (0-100).
        intent_score: Intent detection score (0-100).
        signals: List of intent signals detected.
        extraction_source: Source of extraction ("json-ld" or "regex").
        confidence: Confidence level (0.0-1.0).
    """

    name: str = Field(default="")
    title: str = Field(default="")
    email: str = Field(default="")
    phone: str = Field(default="")
    company: str = Field(default="")
    domain: str = Field(...)
    score: int = Field(default=0)
    intent_score: int = Field(default=0)
    signals: list[str] = Field(default_factory=list)
    extraction_source: str = Field(default="")
    confidence: float = Field(default=0.0)

    def to_ghl_payload(self) -> dict:
        """Convert Lead to GoHighLevel API payload format.

        Gracefully handles empty fields by omitting them from the payload.

        Returns:
            Dictionary suitable for GHL contact creation/update API.
        """
        payload: dict[str, str | int | float | list] = {}

        if self.name:
            payload["name"] = self.name
        if self.title:
            payload["title"] = self.title
        if self.email:
            payload["email"] = self.email
        if self.phone:
            payload["phone"] = self.phone
        if self.company:
            payload["company"] = self.company
        if self.domain:
            payload["domain"] = self.domain
        if self.score:
            payload["score"] = self.score
        if self.intent_score:
            payload["intent_score"] = self.intent_score
        if self.signals:
            payload["signals"] = self.signals
        if self.extraction_source:
            payload["extraction_source"] = self.extraction_source
        if self.confidence:
            payload["confidence"] = self.confidence

        return payload
