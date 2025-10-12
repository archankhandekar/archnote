"""Agent responsible for formatting raw clinical notes."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Tuple

from importlib import resources

from .dates import normalize_dates_in_text
from .sections import SectionResult, extract_sections


@dataclass
class FormatterArtifacts:
    """Intermediate artifacts gathered during formatting for observability."""

    normalized_input: str
    sections: SectionResult
    investigations_block: str
    template: str


def load_template() -> str:
    """Load the clinical note template from packaged resources."""

    return resources.files("archnote.prompts").joinpath("clinical_note_template.md").read_text()


def normalize_whitespace(text: str) -> str:
    """Compress repeated whitespace while preserving paragraph breaks."""

    stripped = text.strip()
    if not stripped:
        return ""
    lines = []
    for line in stripped.splitlines():
        parts = [segment for segment in line.strip().split() if segment]
        lines.append(" ".join(parts))
    return "\n".join(lines)


def limit_sentences(text: str, max_sentences: int = 2) -> str:
    """Limit text to ``max_sentences`` sentences while preserving punctuation."""

    stripped = text.strip()
    if not stripped:
        return stripped
    sentences = re.split(r"(?<=[.!?])\s+", stripped)
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    return " ".join(sentences[:max_sentences])


def build_investigations(sections: Dict[str, str]) -> str:
    """Compose the investigations portion of the note with normalized dates."""

    parts = []
    for key, heading in (("investigations", "Investigations"), ("labs", "Labs"), ("imaging", "Imaging")):
        block = sections.get(key)
        if block:
            normalized, _ = normalize_dates_in_text(block)
            parts.append(f"{heading}:\n{normalized.strip()}")
    if not parts:
        return "No investigations documented."
    return "\n\n".join(parts)


def format_note(raw_note: str, *, return_artifacts: bool = False) -> str | Tuple[str, FormatterArtifacts]:
    """Normalize and structure ``raw_note`` into the clinical template."""

    normalized_input = normalize_whitespace(raw_note)
    section_result = extract_sections(normalized_input)

    sections = section_result.sections
    hpi = sections.get("hpi") or section_result.residual or normalized_input
    investigations_block = build_investigations(sections)
    assessment = limit_sentences(sections.get("assessment", "")) or "No assessment documented."
    plan = sections.get("plan", "") or "No plan documented."

    template = load_template()
    formatted = template.format(
        hpi=hpi.strip() or "No HPI documented.",
        investigations=investigations_block.strip(),
        assessment=assessment.strip(),
        plan=plan.strip(),
    ).strip()

    if return_artifacts:
        artifacts = FormatterArtifacts(
            normalized_input=normalized_input,
            sections=section_result,
            investigations_block=investigations_block,
            template=template,
        )
        return formatted, artifacts
    return formatted
