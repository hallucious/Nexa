from __future__ import annotations

from src.designer.proposal_flow import get_starter_circuit_template, list_starter_circuit_templates


def test_list_starter_circuit_templates_returns_representative_validated_set() -> None:
    templates = list_starter_circuit_templates()

    assert len(templates) == 10
    assert templates[0].template_id == "text_summarizer"
    assert all(template.designer_request_text for template in templates)


def test_get_starter_circuit_template_returns_specific_template() -> None:
    template = get_starter_circuit_template("code_reviewer")

    assert template.display_name == "Code Reviewer"
    assert template.category == "code"
    assert "code" in template.designer_request_text.lower()
