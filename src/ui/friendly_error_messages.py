from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any

from src.contracts.status_taxonomy import lookup_reason_code_record
from src.ui.i18n import ui_text


@dataclass(frozen=True)
class FriendlyErrorView:
    visible: bool = False
    error_code: str | None = None
    title: str | None = None
    message: str | None = None
    action_label: str | None = None
    action_target: str | None = None
    source_kind: str | None = None


def _build_view(error_code: str, *, app_language: str, source_kind: str | None) -> FriendlyErrorView:
    return FriendlyErrorView(
        visible=True,
        error_code=error_code,
        title=ui_text(f"friendly_error.{error_code}.title", app_language=app_language),
        message=ui_text(f"friendly_error.{error_code}.message", app_language=app_language),
        action_label=ui_text(f"friendly_error.{error_code}.action", app_language=app_language),
        action_target={
            "API_KEY_MISSING": "provider_setup",
            "PROVIDER_TIMEOUT": "retry_run",
            "QUOTA_EXCEEDED": "open_quota",
            "INPUT_SAFETY_BLOCKED": "review_input",
            "NETWORK_ERROR": "retry_run",
        }.get(error_code),
        source_kind=source_kind,
    )


def _detect_from_reason_code(reason_code: str | None, *, source_kind: str | None) -> str | None:
    if not isinstance(reason_code, str) or not reason_code:
        return None
    if reason_code.startswith("quota."):
        return "QUOTA_EXCEEDED"
    if reason_code.startswith("safety."):
        record = lookup_reason_code_record(reason_code)
        if record is not None and record.severity in {"blocking", "warning"}:
            return "INPUT_SAFETY_BLOCKED"
    return None


_API_KEY_MARKERS = (
    "api key",
    "openai_api_key",
    "anthropic_api_key",
    "gemini_api_key",
    "perplexity_api_key",
    "missing key",
    "key not configured",
    "provider key",
)
_TIMEOUT_MARKERS = ("timeout", "timed out", "provider timeout")
_NETWORK_MARKERS = (
    "network",
    "connection",
    "dns",
    "unreachable",
    "temporarily unavailable",
    "connection reset",
    "connection refused",
)


def _detect_from_issue_or_message(issue_code: str | None, message: str | None) -> str | None:
    code_upper = issue_code.upper() if isinstance(issue_code, str) else ""
    text = (message or "").lower()
    if code_upper == "API_KEY_MISSING" or any(marker in text for marker in _API_KEY_MARKERS):
        return "API_KEY_MISSING"
    if code_upper == "PROVIDER_TIMEOUT" or code_upper == "AI.TIMEOUT" or any(marker in text for marker in _TIMEOUT_MARKERS):
        return "PROVIDER_TIMEOUT"
    if code_upper == "QUOTA_EXCEEDED":
        return "QUOTA_EXCEEDED"
    if code_upper == "INPUT_SAFETY_BLOCKED":
        return "INPUT_SAFETY_BLOCKED"
    if code_upper == "NETWORK_ERROR" or any(marker in text for marker in _NETWORK_MARKERS):
        return "NETWORK_ERROR"
    return None


def friendly_error_from_candidates(*, app_language: str, candidates: Iterable[Mapping[str, Any]]) -> FriendlyErrorView:
    for candidate in candidates:
        source_kind = str(candidate.get("source_kind")) if candidate.get("source_kind") is not None else None
        error_code = _detect_from_reason_code(candidate.get("reason_code"), source_kind=source_kind)
        if error_code is None:
            error_code = _detect_from_issue_or_message(
                candidate.get("issue_code") if isinstance(candidate.get("issue_code"), str) else None,
                candidate.get("message") if isinstance(candidate.get("message"), str) else None,
            )
        if error_code is not None:
            return _build_view(error_code, app_language=app_language, source_kind=source_kind)
    return FriendlyErrorView()


__all__ = ["FriendlyErrorView", "friendly_error_from_candidates"]
