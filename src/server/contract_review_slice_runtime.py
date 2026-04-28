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


__all__ = ["ContractReviewSliceView", "contract_review_slice_payload", "contract_review_slice_view"]
