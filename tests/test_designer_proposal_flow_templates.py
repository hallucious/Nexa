from __future__ import annotations

from src.designer.proposal_flow import get_starter_circuit_template, list_starter_circuit_templates


def test_list_starter_circuit_templates_returns_representative_validated_set() -> None:
    templates = list_starter_circuit_templates()

    assert len(templates) == 10
    assert templates[0].template_id == "text_summarizer"
    assert all(template.designer_request_text for template in templates)
    assert all(template.template_version == "1.0" for template in templates)
    assert all(template.provenance_family == "starter-template" for template in templates)
    assert all(template.provenance_source == "nexa-curated" for template in templates)
    assert all(template.curation_status == "curated" for template in templates)
    assert all(template.compatibility_family == "workspace-shell-draft" for template in templates)
    assert all(template.apply_behavior == "replace_designer_request" for template in templates)
    assert all(template.supported_storage_roles == ("working_save",) for template in templates)


def test_get_starter_circuit_template_returns_specific_template() -> None:
    template = get_starter_circuit_template("code_reviewer")

    assert template.display_name == "Code Reviewer"
    assert template.category == "code"
    assert "code" in template.designer_request_text.lower()
    assert template.provenance_source == "nexa-curated"
    assert template.supported_entry_surfaces == ("designer", "template_gallery")
    assert template.template_ref == "nexa-curated:code_reviewer@1.0"


def test_get_starter_circuit_template_accepts_canonical_template_ref() -> None:
    template = get_starter_circuit_template("nexa-curated:code_reviewer@1.0")

    assert template.template_id == "code_reviewer"
    assert template.template_ref == "nexa-curated:code_reviewer@1.0"
