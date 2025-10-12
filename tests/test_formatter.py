from __future__ import annotations

from archnote.formatter.agent import format_note, load_template
from archnote.formatter.note_editor import append_visit_to_note
from archnote.formatter.dates import normalize_dates_in_text
from archnote.formatter.sections import extract_sections


def test_format_note_applies_template_and_limits_assessment():
    raw_note = """
    HPI:
    Patient reports cough for three days and mild fever.

    Labs:
    CBC 5/12/23 within normal limits.

    Imaging:
    Chest X-ray Jan 2, 2024 clear.

    Assessment:
    Viral upper respiratory infection suspected. Consider allergies. Await culture results.

    Plan:
    Symptomatic treatment and follow-up next week.
    """

    formatted, artifacts = format_note(raw_note, return_artifacts=True)

    assert "2023-05-12" in artifacts.investigations_block
    assert "2024-01-02" in artifacts.investigations_block
    assert "Await culture results" not in formatted
    template = load_template()
    assert formatted.startswith("# Clinical Note Template")
    assert "## Assessment" in formatted


def test_extract_sections_handles_text_without_headings():
    raw_note = "Patient describes worsening fatigue over two weeks. Plan to repeat labs 3/1/24."
    result = extract_sections(raw_note)
    assert result.sections == {}
    assert "fatigue" in result.residual

    formatted = format_note(raw_note)
    assert "History of Present Illness" in formatted
    assert "No plan documented" in formatted


def test_normalize_dates_in_text_preserves_unparseable_dates():
    text = "Labs drawn 13/40/2023 and imaging pending 4/31/22."
    normalized, replacements = normalize_dates_in_text(text)
    assert normalized == text
    assert replacements == []


def test_format_note_investigations_defaults():
    raw_note = """
    History of Present Illness
    OCR like spacing with random CAPITALIZATION.

    ASSESSMENT
    Condition stable.
    """
    formatted = format_note(raw_note)
    assert "No investigations documented" in formatted
    assert "Condition stable" in formatted


def test_append_visit_to_note_replaces_default_text():
    formatted = format_note("Patient seen in clinic.")

    updated = append_visit_to_note(
        formatted,
        "Follow-up labs on 2/14/24: CBC within range.",
        visit_label="Clinic follow-up",
    )

    assert "No investigations documented" not in updated
    assert "Clinic follow-up" in updated
    assert "2024-02-14" in updated


def test_append_visit_to_note_appends_multiple_entries():
    raw_note = """
    HPI:
    Patient with chronic condition.

    Investigations:
    Baseline labs 1/5/24 WNL.
    """
    formatted = format_note(raw_note)

    first_update = append_visit_to_note(
        formatted,
        "MRI 3/10/24: No new lesions.",
        visit_label="Radiology",
        visit_date="March 10, 2024",
    )

    second_update = append_visit_to_note(
        first_update,
        "Labs 04/02/24 elevated AST.",
        visit_label="Hepatology",
        visit_date="04/02/24",
    )

    assert second_update.count("###") == 2
    assert "2024-03-10" in second_update
    assert "2024-04-02" in second_update
