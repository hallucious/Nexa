from __future__ import annotations

from src.engine.representation_model import ComparableUnit, Representation
from src.engine.text_extractor import extract_text_representation


def test_extract_text_representation_returns_representation():
    result = extract_text_representation("## Morning\nhello")

    assert isinstance(result, Representation)
    assert result.artifact_type == "text"
    assert result.metadata["unit_count"] == 1


def test_extract_text_representation_creates_multiple_section_units():
    text = "\n".join(
        [
            "## Morning",
            "alpha",
            "### Lunch",
            "beta",
            "## Evening",
            "gamma",
        ]
    )

    result = extract_text_representation(text)

    assert len(result.units) == 3
    assert [unit.unit_kind for unit in result.units] == ["section", "section", "section"]
    assert [unit.metadata["heading"] for unit in result.units] == ["Morning", "Lunch", "Evening"]
    assert [unit.metadata["position"] for unit in result.units] == [0, 1, 2]


def test_canonical_label_normalization_uses_first_word_lowercased():
    text = "\n".join(
        [
            "## Morning (Asakusa)",
            "alpha",
            "### Lunch - Ueno",
            "beta",
            "## Evening: Ginza",
            "gamma",
        ]
    )

    result = extract_text_representation(text)

    assert [unit.canonical_label for unit in result.units] == ["morning", "lunch", "evening"]


def test_no_heading_case_creates_single_fallback_unit():
    text = "plain line one\nplain line two"

    result = extract_text_representation(text)

    assert len(result.units) == 1
    unit = result.units[0]
    assert isinstance(unit, ComparableUnit)
    assert unit.unit_kind == "section"
    assert unit.canonical_label is None
    assert unit.payload == text
    assert unit.metadata["heading"] is None
    assert result.metadata["heading_mode"] is False


def test_representation_id_is_deterministic_for_same_input():
    text = "## Morning\nhello\n## Evening\nbye"

    first = extract_text_representation(text)
    second = extract_text_representation(text)

    assert first.representation_id == second.representation_id
    assert first.to_dict() == second.to_dict()


def test_representation_id_changes_when_text_changes():
    first = extract_text_representation("## Morning\nhello")
    second = extract_text_representation("## Morning\nhello!")

    assert first.representation_id != second.representation_id
