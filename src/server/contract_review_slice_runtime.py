from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote


@dataclass(frozen=True)
class ContractReviewSliceView:
    """Browser-facing contract-review vertical slice metadata."""

    template_id: str
    title: str
    summary: str
    accepted_file_types: tuple[str, ...]
    accepted_mime_types: tuple[str, ...]
    required_upload_state: str
    run_intent: str
    default_model_tier: str
    output_contract: tuple[str, ...]
    source_reference_mode: str
    next_actions: tuple[str, ...]
    upload_href: str
    run_href: str
    result_href: str

    def as_payload(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "title": self.title,
            "summary": self.summary,
            "accepted_file_types": list(self.accepted_file_types),
            "accepted_mime_types": list(self.accepted_mime_types),
            "required_upload_state": self.required_upload_state,
            "run_intent": self.run_intent,
            "default_model_tier": self.default_model_tier,
            "output_contract": list(self.output_contract),
            "source_reference_mode": self.source_reference_mode,
            "next_actions": list(self.next_actions),
            "upload_href": self.upload_href,
            "run_href": self.run_href,
            "result_href": self.result_href,
        }


@dataclass(frozen=True)
class ContractReviewRunInputHandoff:
    """Browser-facing safe-upload to contract-review run input handoff."""

    use_case: str
    template_id: str
    workspace_id: str
    upload_id: str | None
    upload_status: str
    extraction_id: str | None
    required_upload_state: str
    ready_for_run: bool
    blocked_reason: str | None
    run_submission_payload: dict[str, Any]

    def as_payload(self) -> dict[str, Any]:
        return {
            "use_case": self.use_case,
            "template_id": self.template_id,
            "workspace_id": self.workspace_id,
            "upload_id": self.upload_id,
            "upload_status": self.upload_status,
            "extraction_id": self.extraction_id,
            "required_upload_state": self.required_upload_state,
            "ready_for_run": self.ready_for_run,
            "blocked_reason": self.blocked_reason,
            "run_submission_payload": self.run_submission_payload,
        }


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def contract_review_slice_view(*, workspace_id: str, app_language: str = "en") -> ContractReviewSliceView:
    safe_workspace_id = quote(str(workspace_id), safe="")
    safe_language = quote(str(app_language or "en"), safe="")
    return ContractReviewSliceView(
        template_id="contract_review_freelancer_v1",
        title="Contract review for freelancers",
        summary="Upload a PDF or DOCX contract, wait until the file is safe, then run the review flow to get clauses, explanations, source references, and pre-signature questions.",
        accepted_file_types=("PDF", "DOCX"),
        accepted_mime_types=("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        required_upload_state="safe",
        run_intent="contract_review",
        default_model_tier="economy",
        output_contract=("document_reference", "clause_list", "plain_language_explanations", "pre_signature_questions", "character_offset_source_references"),
        source_reference_mode="character_offsets",
        next_actions=("copy_result", "continue_from_selected_result", "ask_pre_signature_question"),
        upload_href=f"/app/workspaces/{safe_workspace_id}/upload?app_language={safe_language}&use_case=contract_review",
        run_href=f"/app/workspaces/{safe_workspace_id}/run?app_language={safe_language}&use_case=contract_review",
        result_href=f"/app/workspaces/{safe_workspace_id}/results?app_language={safe_language}&use_case=contract_review",
    )


def contract_review_slice_payload(*, workspace_id: str, app_language: str = "en") -> dict[str, Any]:
    return contract_review_slice_view(workspace_id=workspace_id, app_language=app_language).as_payload()


def contract_review_run_input_handoff(
    *,
    workspace_id: str,
    app_language: str = "en",
    upload_id: Any | None = None,
    upload_status: Any | None = None,
    extraction_id: Any | None = None,
) -> ContractReviewRunInputHandoff:
    slice_view = contract_review_slice_view(workspace_id=workspace_id, app_language=app_language)
    normalized_upload_id = _optional_text(upload_id)
    normalized_extraction_id = _optional_text(extraction_id)
    normalized_upload_status = (_optional_text(upload_status) or "unknown").lower()
    ready_for_run = bool(normalized_upload_id) and normalized_upload_status == slice_view.required_upload_state
    blocked_reason = None
    if not normalized_upload_id:
        blocked_reason = "contract_review.upload_required"
    elif normalized_upload_status != slice_view.required_upload_state:
        blocked_reason = "contract_review.upload_not_safe"
    run_submission_payload = {
        "workspace_id": str(workspace_id),
        "execution_target": {
            "target_type": "approved_snapshot",
            "target_ref": "latest",
        },
        "input_payload": {
            "run_intent": slice_view.run_intent,
            "use_case": "contract_review",
            "template_id": slice_view.template_id,
            "document_reference": {
                "upload_id": normalized_upload_id,
                "upload_status": normalized_upload_status,
                "extraction_id": normalized_extraction_id,
                "required_upload_state": slice_view.required_upload_state,
            },
            "output_contract": list(slice_view.output_contract),
            "source_reference_mode": slice_view.source_reference_mode,
        },
        "launch_options": {
            "launch_source": "web_contract_review_slice",
            "model_tier": slice_view.default_model_tier,
        },
        "client_context": {
            "surface": "web_run_entry",
            "use_case": "contract_review",
            "ready_for_run": ready_for_run,
        },
    }
    return ContractReviewRunInputHandoff(
        use_case="contract_review",
        template_id=slice_view.template_id,
        workspace_id=str(workspace_id),
        upload_id=normalized_upload_id,
        upload_status=normalized_upload_status,
        extraction_id=normalized_extraction_id,
        required_upload_state=slice_view.required_upload_state,
        ready_for_run=ready_for_run,
        blocked_reason=blocked_reason,
        run_submission_payload=run_submission_payload,
    )


def contract_review_run_input_handoff_payload(
    *,
    workspace_id: str,
    app_language: str = "en",
    upload_id: Any | None = None,
    upload_status: Any | None = None,
    extraction_id: Any | None = None,
) -> dict[str, Any]:
    return contract_review_run_input_handoff(
        workspace_id=workspace_id,
        app_language=app_language,
        upload_id=upload_id,
        upload_status=upload_status,
        extraction_id=extraction_id,
    ).as_payload()


__all__ = [
    "ContractReviewRunInputHandoff",
    "ContractReviewSliceView",
    "contract_review_run_input_handoff",
    "contract_review_run_input_handoff_payload",
    "contract_review_slice_payload",
    "contract_review_slice_view",
]
