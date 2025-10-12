"""Utilities for editing previously formatted clinical notes."""
from __future__ import annotations

import textwrap
from typing import Tuple

from .dates import normalize_date, normalize_dates_in_text


class InvestigationsSectionMissingError(ValueError):
    """Raised when a formatted note does not contain an investigations section."""


def _locate_investigations_section(note: str) -> Tuple[int, int, int]:
    """Return tuple of indices delimiting the investigations block.

    The return value is ``(body_start, body_end, next_heading_start)`` where
    ``body_start`` and ``body_end`` bound the investigations content and
    ``next_heading_start`` is the index of the heading that follows the
    investigations block (or ``len(note)`` if it is the final section).
    """

    heading = "## Investigations"
    heading_index = note.find(heading)
    if heading_index == -1:
        raise InvestigationsSectionMissingError(
            "Existing note does not contain an investigations section."
        )

    # Find the start of the body immediately after the heading newline.
    newline_index = note.find("\n", heading_index + len(heading))
    if newline_index == -1:
        body_start = heading_index + len(heading)
    else:
        body_start = newline_index + 1

    next_heading = note.find("\n## ", body_start)
    if next_heading == -1:
        body_end = len(note)
        next_heading_start = len(note)
    else:
        body_end = next_heading
        next_heading_start = next_heading

    return body_start, body_end, next_heading_start


def append_visit_to_note(
    existing_note: str,
    visit_report: str,
    *,
    visit_date: str | None = None,
    visit_label: str | None = None,
) -> str:
    """Append a new visit report into the investigations block of a note.

    Parameters
    ----------
    existing_note:
        A previously formatted note that follows the bundled clinical template.
    visit_report:
        Free-text description of the new investigations or reports collected
        during the additional visit.
    visit_date:
        Optional date associated with the visit. When supplied the value is
        normalized to ISO format when possible.
    visit_label:
        Optional textual label (e.g., "Cardiology follow-up").
    """

    if not visit_report.strip():
        raise ValueError("visit_report must contain content to append.")

    body_start, body_end, _ = _locate_investigations_section(existing_note)

    existing_body = existing_note[body_start:body_end].strip()

    normalized_report, _ = normalize_dates_in_text(visit_report)
    cleaned_report = textwrap.dedent(normalized_report).strip()

    title_parts = []
    if visit_label and visit_label.strip():
        title_parts.append(visit_label.strip())
    if visit_date and visit_date.strip():
        normalized_date = normalize_date(visit_date.strip()) or visit_date.strip()
        title_parts.append(normalized_date)

    if title_parts:
        entry = f"### {' – '.join(title_parts)}\n{cleaned_report}"
    else:
        entry = cleaned_report

    if not existing_body or existing_body == "No investigations documented.":
        combined_body = entry
    else:
        combined_body = f"{existing_body}\n\n{entry}"

    prefix = existing_note[:body_start]
    suffix = existing_note[body_end:]

    updated_body = combined_body.strip()

    rebuilt = prefix
    if not rebuilt.endswith("\n"):
        rebuilt += "\n"
    rebuilt += updated_body + "\n\n"
    rebuilt += suffix.lstrip("\n")

    return rebuilt


__all__ = ["append_visit_to_note", "InvestigationsSectionMissingError"]
