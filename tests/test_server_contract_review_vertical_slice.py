from __future__ import annotations

from src.server.contract_review_slice_runtime import contract_review_next_action_panel_payload, contract_review_run_input_handoff_payload, contract_review_slice_payload, contract_review_structured_result_payload
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


def test_contract_review_run_input_handoff_requires_safe_upload() -> None:
    blocked = contract_review_run_input_handoff_payload(
        workspace_id="ws-001",
        app_language="en",
        upload_id="upload-001",
        upload_status="scanning",
    )

    assert blocked["use_case"] == "contract_review"
    assert blocked["ready_for_run"] is False
    assert blocked["blocked_reason"] == "contract_review.upload_not_safe"
    assert blocked["run_submission_payload"]["input_payload"]["document_reference"]["upload_status"] == "scanning"

    ready = contract_review_run_input_handoff_payload(
        workspace_id="ws-001",
        app_language="en",
        upload_id="upload-001",
        upload_status="safe",
        extraction_id="extract-001",
    )

    assert ready["ready_for_run"] is True
    assert ready["blocked_reason"] is None
    assert ready["run_submission_payload"]["workspace_id"] == "ws-001"
    assert ready["run_submission_payload"]["input_payload"]["run_intent"] == "contract_review"
    assert ready["run_submission_payload"]["input_payload"]["document_reference"] == {
        "upload_id": "upload-001",
        "upload_status": "safe",
        "extraction_id": "extract-001",
        "required_upload_state": "safe",
    }
    assert "clause_list" in ready["run_submission_payload"]["input_payload"]["output_contract"]


def test_contract_review_run_page_exposes_safe_upload_handoff_payload() -> None:
    html = render_web_run_entry_html(
        workspace_id="ws-001",
        app_language="en",
        use_case="contract_review",
        upload_id="upload-001",
        upload_status="safe",
        extraction_id="extract-001",
    )

    assert "contract-review-run-input-handoff" in html
    assert 'data-upload-id="upload-001"' in html
    assert 'data-upload-status="safe"' in html
    assert 'data-extraction-id="extract-001"' in html
    assert 'data-ready-for-run="true"' in html
    assert "web_contract_review_slice" in html
    assert "contract_review_freelancer_v1" in html
    assert "character_offset_source_references" in html


def test_contract_review_structured_result_payload_projects_clause_questions_and_sources() -> None:
    payload = contract_review_structured_result_payload(
        output_key="contract_review_result",
        value_type="contract_review",
        value_preview=(
            '{'
            '"use_case":"contract_review",'
            '"template_id":"contract_review_freelancer_v1",'
            '"document_reference":{"upload_id":"upload-001","extraction_id":"extract-001"},'
            '"clauses":[{"clause_id":"payment","title":"Payment terms","risk_level":"medium",'
            '"plain_language_explanation":"Payment timing is not explicit.",'
            '"source_reference":{"start":120,"end":180,"label":"Section 3"}}],'
            '"pre_signature_questions":["When is payment due?"]'
            '}'
        ),
    )

    assert payload is not None
    assert payload["render_kind"] == "contract_review_structured"
    assert payload["template_id"] == "contract_review_freelancer_v1"
    assert payload["document_reference"] == {"upload_id": "upload-001", "extraction_id": "extract-001"}
    assert payload["clauses"][0]["title"] == "Payment terms"
    assert payload["clauses"][0]["risk_level"] == "medium"
    assert payload["clauses"][0]["source_reference"] == {
        "mode": "character_offsets",
        "start": 120,
        "end": 180,
        "label": "Section 3",
    }
    assert payload["pre_signature_questions"] == ["When is payment due?"]
    assert "ask_pre_signature_question" in payload["next_actions"]


def test_contract_review_next_action_panel_preserves_copy_continue_and_question_actions() -> None:
    structured = contract_review_structured_result_payload(
        output_key="contract_review_result",
        value_type="contract_review",
        value_preview=(
            '{'
            '"use_case":"contract_review",'
            '"template_id":"contract_review_freelancer_v1",'
            '"document_reference":{"upload_id":"upload-001","extraction_id":"extract-001"},'
            '"clauses":[{"clause_id":"payment","title":"Payment terms","risk_level":"medium",'
            '"plain_language_explanation":"Payment timing is not explicit.",'
            '"source_reference":{"start":120,"end":180,"label":"Section 3"}}],'
            '"pre_signature_questions":["When is payment due?"]'
            '}'
        ),
    )

    panel = contract_review_next_action_panel_payload(
        workspace_id="ws-001",
        run_id="run-002",
        output_ref="contract_review_result",
        contract_review_result=structured,
        app_language="en",
    )

    assert panel is not None
    assert panel["actions"][0]["action_id"] == "copy_contract_review_result"
    assert panel["actions"][0]["action_kind"] == "copy_output"
    assert "Payment timing is not explicit." in panel["actions"][0]["copy_text"]
    assert panel["actions"][1]["action_id"] == "continue_from_contract_review_result"
    assert "return_use=contract_review_result" in panel["actions"][1]["href"]
    assert panel["question_actions"][0]["question_id"] == "question-1"
    assert panel["question_actions"][0]["action_kind"] == "designer_followup"
    assert "return_use=contract_review_question" in panel["question_actions"][0]["href"]
    assert "When is payment due?" in panel["question_actions"][0]["prompt_text"]
