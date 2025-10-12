"""Utilities for parsing and normalizing dates found in raw clinical notes."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, List, Tuple

DATE_PATTERNS: Tuple[Tuple[re.Pattern[str], Iterable[str]], ...] = (
    (
        re.compile(r"\b(?P<month>\d{1,2})[/-](?P<day>\d{1,2})[/-](?P<year>\d{2,4})\b"),
        ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y"),
    ),
    (
        re.compile(
            r"\b(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
            r"\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?(?:,)?\s+(?P<year>\d{2,4})\b",
            re.IGNORECASE,
        ),
        (
            "%B %d, %Y",
            "%b %d, %Y",
            "%B %d %Y",
            "%b %d %Y",
            "%B %d, %y",
            "%b %d, %y",
            "%B %d %y",
            "%b %d %y",
        ),
    ),
)

MONTH_LOOKUP = {
    "jan": "January",
    "feb": "February",
    "mar": "March",
    "apr": "April",
    "may": "May",
    "jun": "June",
    "jul": "July",
    "aug": "August",
    "sep": "September",
    "sept": "September",
    "oct": "October",
    "nov": "November",
    "dec": "December",
}


def normalize_date(date_str: str) -> str | None:
    """Attempt to normalize a free-text date string to ISO format (YYYY-MM-DD).

    Returns ``None`` if no normalization is possible.
    """

    cleaned = date_str.strip()
    for pattern, formats in DATE_PATTERNS:
        if pattern.search(cleaned):
            for fmt in formats:
                try:
                    return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
            # For month name patterns, lowercase and expand month before parsing.
            if pattern.groups >= 3:
                parts = pattern.search(cleaned)
                if parts:
                    month = parts.group("month")
                    if month:
                        month_lower = month.lower()[:3]
                        month_full = MONTH_LOOKUP.get(month_lower)
                        if month_full:
                            rebuilt = cleaned.replace(month, month_full)
                            for fmt in formats:
                                try:
                                    return datetime.strptime(rebuilt, fmt).strftime("%Y-%m-%d")
                                except ValueError:
                                    continue
    return None


def normalize_dates_in_text(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    """Replace dates in ``text`` with ISO-normalized versions.

    Returns the normalized text along with a list of tuples of
    ``(original_date, normalized_date)`` for traceability.
    """

    replacements: List[Tuple[str, str]] = []

    def replace(match: re.Match[str]) -> str:
        date_str = match.group(0)
        normalized = normalize_date(date_str)
        if normalized:
            replacements.append((date_str, normalized))
            return normalized
        return date_str

    normalized_text = text
    for pattern, _ in DATE_PATTERNS:
        normalized_text = pattern.sub(replace, normalized_text)
    return normalized_text, replacements
