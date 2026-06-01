"""Identity extractor for extracting name, title, email from HTML."""

import json
import logging
import re
from typing import Any

from lxml import etree, html as lxml_html

from src.models.lead import Lead

logger = logging.getLogger(__name__)


# Bogus name filters
CITY_NAMES = {
    "london", "paris", "tokyo", "berlin", "moscow", "beijing", "shanghai",
    "new york", "los angeles", "chicago", "houston", "phoenix", "philadelphia"
}

LAW_TERMS = {
    "attorney", "lawyer", "counsel", "legal", "law firm", "llp", "pc", "pllc"
}


def _parse_json_ld(html_content: str) -> list[dict[str, Any]]:
    """Parse JSON-LD Person schemas from HTML.

    Args:
        html_content: Raw HTML content.

    Returns:
        List of person data dictionaries extracted from JSON-LD.
    """
    persons = []
    try:
        tree = lxml_html.fromstring(html_content)
        scripts = tree.xpath('//script[@type="application/ld+json"]/text()')

        for script in scripts:
            try:
                data = json.loads(script.strip())
                # Handle array of schemas
                if isinstance(data, list):
                    schemas = data
                else:
                    schemas = [data]

                for schema in schemas:
                    if not isinstance(schema, dict):
                        continue
                    schema_type = schema.get("@type", "")
                    if schema_type == "Person":
                        person_data = {
                            "name": schema.get("name", ""),
                            "jobTitle": schema.get("jobTitle", ""),
                            "email": schema.get("email", ""),
                            "telephone": schema.get("telephone", ""),
                            "worksFor": schema.get("worksFor", {}),
                        }
                        # Extract company name if worksFor is a dict or string
                        company = person_data["worksFor"]
                        if isinstance(company, dict):
                            person_data["company"] = company.get("name", "")
                        elif isinstance(company, str):
                            person_data["company"] = company
                        else:
                            person_data["company"] = ""
                        persons.append(person_data)
                    elif schema_type == "Organization":
                        # Check for member/employee persons
                        members = schema.get("member", [])
                        if isinstance(members, list):
                            for member in members:
                                if isinstance(member, dict) and member.get("@type") == "Person":
                                    person_data = {
                                        "name": member.get("name", ""),
                                        "jobTitle": member.get("jobTitle", ""),
                                        "email": member.get("email", ""),
                                        "telephone": member.get("telephone", ""),
                                        "company": schema.get("name", ""),
                                    }
                                    persons.append(person_data)
            except json.JSONDecodeError:
                logger.debug("Failed to parse JSON-LD script block")
    except Exception as e:
        logger.warning(f"Error parsing JSON-LD: {e}")

    return persons


def _extract_visible_text(html_content: str) -> str:
    """Extract visible text from HTML.

    Args:
        html_content: Raw HTML content.

    Returns:
        Visible text content.
    """
    try:
        tree = lxml_html.fromstring(html_content)
        # Remove script and style elements
        for element in tree.xpath("//script | //style"):
            element.drop_tree()
        text = tree.text_content()
        return text.strip()
    except Exception as e:
        logger.warning(f"Error extracting visible text: {e}")
        return ""


def _regex_extract_names(text: str) -> list[dict[str, str]]:
    """Extract names and titles using regex patterns on visible text.

    Looks for "Name, Title" patterns commonly found on websites.

    Args:
        text: Visible text content.

    Returns:
        List of dicts with name and title.
    """
    results = []
    # Pattern: "Name, Title" or "Name - Title"
    patterns = [
        r'([A-Z][a-z]+\s+[A-Z][a-z]+),\s*([A-Za-z\s]+(?:CEO|Founder|Director|VP|President|Manager))',
        r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*-\s*([A-Za-z\s]+(?:CEO|Founder|Director|VP|President|Manager))',
        r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+([A-Z][a-z\s]+(?:CEO|Founder|Director|VP|President|Manager))',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            results.append({
                "name": match[0].strip(),
                "jobTitle": match[1].strip(),
            })

    return results


def _generate_email_patterns(name: str, domain: str) -> list[str]:
    """Generate common email patterns for a name and domain.

    Args:
        name: Full name.
        domain: Domain name.

    Returns:
        List of generated email addresses.
    """
    if not name or not domain:
        return []

    parts = name.lower().split()
    if len(parts) < 2:
        return []

    first = parts[0]
    last = parts[-1]
    first_initial = first[0] if first else ""

    emails = []
    # first.last@domain
    if first and last:
        emails.append(f"{first}.{last}@{domain}")
    # f.last@domain
    if first_initial and last:
        emails.append(f"{first_initial}.{last}@{domain}")
    # first@domain
    if first:
        emails.append(f"{first}@{domain}")

    return emails


def _is_bogus_name(name: str) -> bool:
    """Filter out bogus names (city names, law terms, <2 words).

    Args:
        name: Name to validate.

    Returns:
        True if name should be filtered out.
    """
    if not name:
        return True

    name_lower = name.lower()
    words = name_lower.split()

    # Less than 2 words
    if len(words) < 2:
        return True

    # City names
    for city in CITY_NAMES:
        if city in name_lower:
            return True

    # Law terms that indicate it's not a person name
    for term in LAW_TERMS:
        if term in name_lower:
            return True

    return False


def extract_identity(html: str, domain: str) -> list[Lead]:
    """Extract identity information from HTML content.

    Step 1: Parse JSON-LD Person schemas
    Step 2: Fallback regex on visible text for "Name, Title" patterns
    Step 3: Generate email patterns if missing
    Step 4: Filter bogus names

    Args:
        html: Raw HTML content.
        domain: Domain name for email generation.

    Returns:
        List of Lead objects with extracted identity data.
    """
    leads = []

    # Step 1: Try JSON-LD extraction
    json_ld_persons = _parse_json_ld(html)

    for person in json_ld_persons:
        name = person.get("name", "") or ""
        title = person.get("jobTitle", "") or ""
        email = person.get("email", "") or ""
        phone = person.get("telephone", "") or ""
        company = person.get("company", "") or ""

        # Skip bogus names
        if _is_bogus_name(name):
            continue

        # Generate email patterns if missing
        if not email:
            generated_emails = _generate_email_patterns(name, domain)
            email = generated_emails[0] if generated_emails else ""

        lead = Lead(
            name=name,
            title=title,
            email=email,
            phone=phone,
            company=company,
            domain=domain,
            extraction_source="json-ld",
        )
        leads.append(lead)

    # Step 2: Fallback to regex extraction if no JSON-LD found
    if not leads:
        visible_text = _extract_visible_text(html)
        regex_matches = _regex_extract_names(visible_text)

        for match in regex_matches:
            name = match.get("name", "")
            title = match.get("jobTitle", "")

            # Skip bogus names
            if _is_bogus_name(name):
                continue

            # Generate email patterns
            generated_emails = _generate_email_patterns(name, domain)
            email = generated_emails[0] if generated_emails else ""

            lead = Lead(
                name=name,
                title=title,
                email=email,
                phone="",
                company="",
                domain=domain,
                extraction_source="regex",
            )
            leads.append(lead)

    logger.info(f"Extracted {len(leads)} identities from {domain}")
    return leads
