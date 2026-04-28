from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Sequence
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
class ContractReviewClauseView:
    """Beginner-readable contract-review clause projection."""

    clause_id: str
    title: str
    risk_level: str
    plain_language_explanation: str
    source_start: int | None = None
    source_end: int | None = None
    source_label: str | None = None

    def as_payload(self) -> dict[str, Any]:
        return {
            "clause_id": self.clause_id,
            "title": self.title,
            "risk_level": self.risk_level,
            "plain_language_explanation": self.plain_language_explanation,
            "source_reference": {
                "mode": "character_offsets",
                "start": self.source_start,
                "end": self.source_end,
                "label": self.source_label,
            },
        }


@dataclass(frozen=True)
class ContractReviewStructuredResultView:
    """Browser-facing structured contract-review result projection."""

    template_id: str
    render_kind: str
    title: str
    summary: str
    document_reference: dict[str, Any]
    clauses: tuple[ContractReviewClauseView, ...]
    pre_signature_questions: tuple[str, ...]
    source_reference_mode: str
    next_actions: tuple[str, ...]

    def as_payload(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "render_kind": self.render_kind,
            "title": self.title,
            "summary": self.summary,
            "document_reference": dict(self.document_reference),
            "clauses": [clause.as_payload() for clause in self.clauses],
            "pre_signature_questions": list(self.pre_signature_questions),
            "source_reference_mode": self.source_reference_mode,
            "next_actions": list(self.next_actions),
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



def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _coerce_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, (list, tuple)):
        return value
    return ()


def _parse_structured_output_text(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, Mapping) else None


def _is_contract_review_structured_candidate(*, output_key: Any = None, value_type: Any = None, parsed_value: Mapping[str, Any] | None = None) -> bool:
    normalized_key = str(output_key or "").strip().lower()
    normalized_type = str(value_type or "").strip().lower()
    if normalized_key in {"contract_review", "contract_review_result", "contract_review_summary"}:
        return True
    if normalized_type in {"contract_review", "contract_review_structured", "structured_contract_review"}:
        return True
    if parsed_value is None:
        return False
    return str(parsed_value.get("use_case") or "").strip().lower() == "contract_review"


def contract_review_structured_result_payload(
    *,
    output_key: Any | None = None,
    value_type: Any | None = None,
    value_preview: Any | None = None,
) -> dict[str, Any] | None:
    parsed_value = _parse_structured_output_text(value_preview)
    if not _is_contract_review_structured_candidate(
        output_key=output_key,
        value_type=value_type,
        parsed_value=parsed_value,
    ):
        return None
    if parsed_value is None:
        return None

    document_reference = _coerce_mapping(parsed_value.get("document_reference")) or {}
    clauses: list[ContractReviewClauseView] = []
    for index, raw_clause in enumerate(_coerce_sequence(parsed_value.get("clauses") or parsed_value.get("clause_list")), start=1):
        clause = _coerce_mapping(raw_clause)
        if clause is None:
            continue
        source_ref = _coerce_mapping(clause.get("source_reference")) or {}
        title = str(clause.get("title") or clause.get("clause_title") or f"Clause {index}").strip()
        explanation = str(
            clause.get("plain_language_explanation")
            or clause.get("explanation")
            or clause.get("summary")
            or ""
        ).strip()
        if not explanation:
            continue
        clauses.append(
            ContractReviewClauseView(
                clause_id=str(clause.get("clause_id") or clause.get("id") or f"clause-{index}"),
                title=title,
                risk_level=str(clause.get("risk_level") or clause.get("risk") or "unknown").strip().lower() or "unknown",
                plain_language_explanation=explanation,
                source_start=_coerce_int(source_ref.get("start") or source_ref.get("start_offset")),
                source_end=_coerce_int(source_ref.get("end") or source_ref.get("end_offset")),
                source_label=str(source_ref.get("label") or source_ref.get("quote") or "").strip() or None,
            )
        )

    questions = tuple(
        str(item).strip()
        for item in _coerce_sequence(parsed_value.get("pre_signature_questions"))
        if str(item).strip()
    )
    view = ContractReviewStructuredResultView(
        template_id=str(parsed_value.get("template_id") or "contract_review_freelancer_v1"),
        render_kind="contract_review_structured",
        title=str(parsed_value.get("title") or "Contract review result").strip(),
        summary=str(parsed_value.get("summary") or "Review the highlighted clauses, source references, and pre-signature questions before signing.").strip(),
        document_reference=dict(document_reference),
        clauses=tuple(clauses),
        pre_signature_questions=questions,
        source_reference_mode="character_offsets",
        next_actions=("copy_result", "continue_from_selected_result", "ask_pre_signature_question"),
    )
    return view.as_payload()


__all__ = [
    "ContractReviewClauseView",
    "ContractReviewRunInputHandoff",
    "ContractReviewStructuredResultView",
    "ContractReviewSliceView",
    "contract_review_run_input_handoff",
    "contract_review_run_input_handoff_payload",
    "contract_review_structured_result_payload",
    "contract_review_slice_payload",
    "contract_review_slice_view",
]
