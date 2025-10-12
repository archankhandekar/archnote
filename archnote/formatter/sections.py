"""Heuristics for identifying structured sections within free-form notes."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

SECTION_PATTERNS: Dict[str, Iterable[str]] = {
    "hpi": [r"HPI", r"History of Present Illness"],
    "assessment": [r"Assessment", r"Impression"],
    "plan": [r"Plan", r"Recommendations"],
    "labs": [r"Labs?", r"Laboratory"],
    "imaging": [r"Imaging", r"Radiology"],
    "investigations": [r"Investigations?"],
}

HEADER_MAP: Dict[str, str] = {}
for canonical, patterns in SECTION_PATTERNS.items():
    for pattern in patterns:
        HEADER_MAP[pattern.lower()] = canonical

HEADER_REGEX = re.compile(
    r"^\s*(?P<header>" + "|".join(pattern for patterns in SECTION_PATTERNS.values() for pattern in patterns) + r")[:\-\s]*$",
    re.IGNORECASE,
)


@dataclass
class SectionResult:
    """Container describing extracted sections."""

    sections: Dict[str, str]
    residual: str


def normalize_heading(heading: str) -> Optional[str]:
    """Map a raw heading to its canonical name."""

    key = heading.strip().lower()
    for pattern, canonical in HEADER_MAP.items():
        if re.fullmatch(pattern, key, re.IGNORECASE):
            return canonical
    return None


def extract_sections(note_text: str) -> SectionResult:
    """Split ``note_text`` into recognized sections using regex-based heuristics."""

    sections: Dict[str, List[str]] = {}
    residual_lines: List[str] = []
    current_section: Optional[str] = None
    buffer: List[str] = []

    lines = note_text.splitlines()
    for line in lines:
        match = HEADER_REGEX.match(line)
        if match:
            if buffer:
                if current_section:
                    sections.setdefault(current_section, []).append("\n".join(buffer).strip())
                else:
                    residual_lines.extend(buffer)
                buffer = []
            heading = match.group("header")
            canonical = normalize_heading(heading)
            current_section = canonical
        else:
            buffer.append(line.rstrip())

    if buffer:
        if current_section:
            sections.setdefault(current_section, []).append("\n".join(buffer).strip())
        else:
            residual_lines.extend(buffer)

    flattened_sections = {key: "\n\n".join(value).strip() for key, value in sections.items() if value}
    residual = "\n".join(line for line in residual_lines if line.strip()).strip()

    return SectionResult(sections=flattened_sections, residual=residual)
