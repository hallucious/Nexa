from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Callable

from src.server.documents.file_reference_gate import (
    FileExtractionSafetyDecision,
    FileUploadSafetyDecision,
    evaluate_input_file_extraction_safety,
    evaluate_input_file_upload_safety,
)
from src.server.provider_catalog_runtime import (
    ProviderModelAccessDecision,
    extract_provider_model_requirements,
    evaluate_provider_model_access_for_artifact,
    resolve_provider_model_cost,
)

FileUploadReader = Callable[[str, str], Any | None]
FileExtractionReader = Callable[[str, str], Any | None]

_SENSITIVE_DETAIL_KEYS = {
    "text",
    "raw_text",
    "document_text",
    "extracted_text",
    "text_content",
    "content",
    "body",
    "text_preview",
    "preview",
}


@dataclass(frozen=True)
class FirstSuccessBlocker:
    """Beginner-safe blocker item for the first-success launch surface."""

    family: str
    reason_code: str
    message: str
    next_action: str
    severity: str = "blocking"
    source_ref: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        family = str(self.family or "").strip()
        reason_code = str(self.reason_code or "").strip()
        message = str(self.message or "").strip()
        next_action = str(self.next_action or "").strip()
        severity = str(self.severity or "").strip().lower()
        if not family:
            raise ValueError("FirstSuccessBlocker.family must be non-empty")
        if not reason_code:
            raise ValueError("FirstSuccessBlocker.reason_code must be non-empty")
        if not message:
            raise ValueError("FirstSuccessBlocker.message must be non-empty")
        if not next_action:
            raise ValueError("FirstSuccessBlocker.next_action must be non-empty")
        if severity not in {"blocking", "warning"}:
            raise ValueError(f"Unsupported FirstSuccessBlocker.severity: {severity}")
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "reason_code", reason_code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "next_action", next_action)
        object.__setattr__(self, "severity", severity)
        object.__setattr__(self, "details", _sanitize_details(self.details))

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "family": self.family,
            "severity": self.severity,
            "reason_code": self.reason_code,
            "message": self.message,
            "next_action": self.next_action,
            "details": dict(self.details),
        }
        if self.source_ref:
            payload["source_ref"] = self.source_ref
        return payload


@dataclass(frozen=True)
class ProviderCostEstimate:
    provider_key: str
    model_ref: str | None
    cost_ratio: float
    pricing_unit: str
    confidence: str = "estimated"

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "provider_key": self.provider_key,
            "cost_ratio": self.cost_ratio,
            "pricing_unit": self.pricing_unit,
            "confidence": self.confidence,
        }
        if self.model_ref:
            payload["model_ref"] = self.model_ref
        return payload


@dataclass(frozen=True)
class FirstSuccessPreflightSummary:
    """2D UI-ready first-success blocker/cost summary.

    This object intentionally contains only beginner-safe metadata. It must not carry
    raw extracted document text, previews, trace snippets, or artifact bodies.
    """

    ready: bool
    blockers: tuple[FirstSuccessBlocker, ...] = ()
    warnings: tuple[FirstSuccessBlocker, ...] = ()
    provider_cost_estimates: tuple[ProviderCostEstimate, ...] = ()
    estimated_total_cost_ratio: float | None = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "ready": self.ready,
            "blockers": [item.to_payload() for item in self.blockers],
            "warnings": [item.to_payload() for item in self.warnings],
            "provider_cost_estimates": [item.to_payload() for item in self.provider_cost_estimates],
        }
        if self.estimated_total_cost_ratio is not None:
            payload["estimated_total_cost_ratio"] = self.estimated_total_cost_ratio
        return payload


def _sanitize_details(value: Mapping[str, object] | None) -> dict[str, object]:
    def sanitize(item: Any) -> Any:
        if isinstance(item, Mapping):
            cleaned: dict[str, object] = {}
            for raw_key, raw_value in item.items():
                key = str(raw_key)
                if key.strip().lower() in _SENSITIVE_DETAIL_KEYS:
                    cleaned[key] = "[redacted]"
                else:
                    cleaned[key] = sanitize(raw_value)
            return cleaned
        if isinstance(item, (list, tuple)):
            return [sanitize(child) for child in item]
        return item

    return dict(sanitize(dict(value or {})))


def _provider_next_action(reason_code: str) -> str:
    if reason_code == "provider_model_access.plan_not_allowed":
        return "Choose an AI model allowed by this plan or change the plan before running."
    if reason_code == "provider_model_access.provider_not_found":
        return "Choose a supported AI provider before running."
    if reason_code == "provider_model_access.model_not_found":
        return "Choose a supported AI model before running."
    return "Review the AI model selection before running."


def _file_upload_next_action(reason_code: str, state: str | None) -> str:
    if reason_code == "file_upload.safety_lookup_unavailable":
        return "Reconnect file safety lookup before running."
    if reason_code == "file_upload.not_found":
        return "Attach the uploaded file again before running."
    if state in {"pending_upload", "quarantine"}:
        return "Finish the file upload before running."
    if state == "scanning":
        return "Wait for file scanning to finish before running."
    if state == "rejected":
        return "Upload a new safe file before running."
    return "Resolve the file safety status before running."


def _file_extraction_next_action(reason_code: str, state: str | None) -> str:
    if reason_code == "file_extraction.safety_lookup_unavailable":
        return "Reconnect document extraction lookup before running."
    if reason_code == "file_extraction.not_found":
        return "Request document text extraction again before running."
    if state in {"queued", "extracting"}:
        return "Wait for document text extraction to finish before running."
    if state in {"failed", "rejected"}:
        return "Fix the document extraction issue or upload a new document before running."
    return "Resolve the document text extraction status before running."


def _blocker_from_provider_decision(decision: ProviderModelAccessDecision) -> FirstSuccessBlocker:
    details: dict[str, object] = {
        "provider_key": decision.provider_key,
        "plan_key": decision.plan_key,
    }
    if decision.model_ref:
        details["model_ref"] = decision.model_ref
    if decision.selected_model_ref:
        details["selected_model_ref"] = decision.selected_model_ref
    if decision.tier:
        details["tier"] = decision.tier
    if decision.cost_ratio is not None:
        details["cost_ratio"] = decision.cost_ratio
    return FirstSuccessBlocker(
        family="provider",
        reason_code=decision.reason_code,
        message=decision.message,
        next_action=_provider_next_action(decision.reason_code),
        source_ref=f"{decision.provider_key}:{decision.model_ref or decision.selected_model_ref or 'default'}",
        details=details,
    )


def _blocker_from_upload_decision(decision: FileUploadSafetyDecision) -> FirstSuccessBlocker:
    return FirstSuccessBlocker(
        family="file_upload",
        reason_code=decision.reason_code,
        message=decision.message,
        next_action=_file_upload_next_action(decision.reason_code, decision.upload_state),
        source_ref=decision.upload_id,
        details={
            "upload_id": decision.upload_id,
            "upload_state": decision.upload_state,
        },
    )


def _blocker_from_extraction_decision(decision: FileExtractionSafetyDecision) -> FirstSuccessBlocker:
    return FirstSuccessBlocker(
        family="file_extraction",
        reason_code=decision.reason_code,
        message=decision.message,
        next_action=_file_extraction_next_action(decision.reason_code, decision.extraction_state),
        source_ref=decision.extraction_id,
        details={
            "extraction_id": decision.extraction_id,
            "extraction_state": decision.extraction_state,
        },
    )


def _provider_cost_estimates(
    *,
    source_payload: Any,
    catalog_rows: Sequence[Mapping[str, Any]] | None,
) -> tuple[ProviderCostEstimate, ...]:
    estimates: list[ProviderCostEstimate] = []
    for requirement in extract_provider_model_requirements(source_payload):
        cost = resolve_provider_model_cost(
            provider_key=requirement.provider_key,
            model_ref=requirement.model_ref,
            catalog_rows=catalog_rows,
        )
        if cost is None:
            continue
        estimates.append(
            ProviderCostEstimate(
                provider_key=cost.provider_key,
                model_ref=cost.model_ref,
                cost_ratio=cost.cost_ratio,
                pricing_unit=cost.pricing_unit,
                confidence="estimated",
            )
        )
    return tuple(estimates)


def build_first_success_preflight_summary(
    *,
    workspace_id: str,
    source_payload: Any,
    input_payload: Any,
    plan_key: str = "free",
    provider_model_catalog_rows: Sequence[Mapping[str, Any]] | None = None,
    file_upload_reader: FileUploadReader | None = None,
    file_extraction_reader: FileExtractionReader | None = None,
    enforce_provider_catalog_access: bool = True,
) -> FirstSuccessPreflightSummary:
    blockers: list[FirstSuccessBlocker] = []

    if enforce_provider_catalog_access:
        provider_decisions = evaluate_provider_model_access_for_artifact(
            source_payload=source_payload,
            plan_key=plan_key,
            catalog_rows=provider_model_catalog_rows,
        )
        blockers.extend(
            _blocker_from_provider_decision(decision)
            for decision in provider_decisions
            if not decision.allowed
        )

    upload_decisions = evaluate_input_file_upload_safety(
        workspace_id=workspace_id,
        input_payload=input_payload,
        file_upload_reader=file_upload_reader,
    )
    blockers.extend(
        _blocker_from_upload_decision(decision)
        for decision in upload_decisions
        if not decision.allowed
    )

    extraction_decisions = evaluate_input_file_extraction_safety(
        workspace_id=workspace_id,
        input_payload=input_payload,
        file_extraction_reader=file_extraction_reader,
    )
    blockers.extend(
        _blocker_from_extraction_decision(decision)
        for decision in extraction_decisions
        if not decision.allowed
    )

    cost_estimates = _provider_cost_estimates(
        source_payload=source_payload,
        catalog_rows=provider_model_catalog_rows,
    )
    total_cost_ratio = sum(item.cost_ratio for item in cost_estimates) if cost_estimates else None

    return FirstSuccessPreflightSummary(
        ready=not blockers,
        blockers=tuple(blockers),
        provider_cost_estimates=cost_estimates,
        estimated_total_cost_ratio=total_cost_ratio,
    )
