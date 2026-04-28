from __future__ import annotations

from src.server.contract_review_slice_runtime import contract_review_slice_payload
from src.server.web_skeleton_runtime import (
    render_web_run_entry_html,
    render_web_upload_entry_html,
    render_web_workspace_dashboard_html,
)


def test_contract_review_slice_payload_defines_minimum_product_contract() -> None:
    payload = contract_review_slice_payload(workspace_id="ws-001", app_language="en")

    assert payload["template_id"] == "contract_review_freelancer_v1"
    assert payload["run_intent"] == "contract_review"
    assert payload["required_upload_state"] == "safe"
    assert payload["default_model_tier"] == "economy"
    assert payload["source_reference_mode"] == "character_offsets"
    assert payload["accepted_file_types"] == ["PDF", "DOCX"]
    assert "clause_list" in payload["output_contract"]
    assert "plain_language_explanations" in payload["output_contract"]
    assert "pre_signature_questions" in payload["output_contract"]
    assert "character_offset_source_references" in payload["output_contract"]
    assert payload["upload_href"].endswith("use_case=contract_review")
    assert payload["run_href"].endswith("use_case=contract_review")
    assert payload["result_href"].endswith("use_case=contract_review")


def test_contract_review_slice_is_visible_from_dashboard_upload_and_run_pages() -> None:
    dashboard_html = render_web_workspace_dashboard_html(
        workspace_rows=[{"workspace_id": "ws-001", "title": "Client NDA"}],
        app_language="en",
    )
    upload_html = render_web_upload_entry_html(workspace_id="ws-001", app_language="en")
    run_html = render_web_run_entry_html(workspace_id="ws-001", app_language="en")

    assert "use_case=contract_review" in dashboard_html
    assert "Contract review" in dashboard_html
    assert "contract-review-upload-readiness" in upload_html
    assert "data-template-id=\"contract_review_freelancer_v1\"" in upload_html
    assert "data-required-upload-state=\"safe\"" in upload_html
    assert "data-accepted-file-types=\"PDF, DOCX\"" in upload_html
    assert "clause_list" in upload_html
    assert "pre_signature_questions" in upload_html
    assert "contract-review-vertical-slice" in run_html
    assert "data-run-intent=\"contract_review\"" in run_html
    assert "data-default-model-tier=\"economy\"" in run_html
    assert "data-source-reference-mode=\"character_offsets\"" in run_html
    assert "plain_language_explanations" in run_html
    assert "character_offset_source_references" in run_html
