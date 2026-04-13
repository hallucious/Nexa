from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Any

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.validation_precheck import ValidationPrecheck, PrecheckFinding
from src.storage.models.execution_record_model import ExecutionIssue, ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.working_save_model import WorkingSaveModel
from src.contracts.status_taxonomy import lookup_reason_code_record
from src.engine.policy_explainability import build_explainability, ExplainabilityResult
from src.engine.execution_regression_policy import PolicyDecision
from src.ui.i18n import beginner_language_enabled, ui_language_from_sources, ui_text
from src.ui.friendly_error_messages import FriendlyErrorView, friendly_error_from_candidates


@dataclass(frozen=True)
class ExplainabilitySummaryView:
    """Explainability projection derived from policy_explainability for the validation surface."""
    status: str = "unavailable"
    summary: str = ""
    structural_issues: list[str] = field(default_factory=list)
    semantic_issues: list[str] = field(default_factory=list)
    verification_contracts: list[str] = field(default_factory=list)
    has_explainability: bool = False


@dataclass(frozen=True)
class ValidationSummaryView:
    blocking_count: int = 0
    warning_count: int = 0
    confirmation_count: int = 0
    info_count: int = 0
    affected_node_count: int = 0
    affected_edge_count: int = 0
    affected_output_count: int = 0
    affected_group_count: int = 0
    top_issue_label: str | None = None
    can_commit: bool = False
    can_execute: bool = False
    requires_user_confirmation: bool = False


@dataclass(frozen=True)
class ValidationFindingView:
    finding_id: str
    severity: str
    category: str
    code: str
    title: str
    message: str
    short_label: str | None = None
    location_ref: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    source_ref: str | None = None
    suggested_action: str | None = None
    docs_ref: str | None = None
    user_confirmation_allowed: bool = False
    auto_resolvable: bool = False
    destructive_risk: bool = False


@dataclass(frozen=True)
class ValidationGroupView:
    group_id: str
    group_label: str
    group_type: str
    findings: list[ValidationFindingView]
    count: int
    collapsed_by_default: bool = False


@dataclass(frozen=True)
class ValidationTargetSummary:
    target_type: str
    target_id: str | None = None
    finding_count: int = 0
    blocking_count: int = 0
    warning_count: int = 0
    confirmation_count: int = 0
    label: str | None = None


@dataclass(frozen=True)
class ValidationActionHint:
    action_type: str
    label: str
    enabled: bool
    reason_disabled: str | None = None


@dataclass(frozen=True)
class ValidationFilterState:
    severity_filter: str = "all"
    category_filter: str = "all"
    target_filter: str = "all"
    search_query: str | None = None


@dataclass(frozen=True)
class BeginnerValidationSummaryView:
    status_signal: str | None = None
    cause: str | None = None
    next_action_type: str | None = None
    next_action_label: str | None = None


@dataclass(frozen=True)
class ValidationPanelViewModel:
    source_mode: str
    storage_role: str
    overall_status: str
    friendly_error: FriendlyErrorView = field(default_factory=FriendlyErrorView)
    beginner_mode: bool = False
    summary: ValidationSummaryView = field(default_factory=ValidationSummaryView)
    blocking_findings: list[ValidationFindingView] = field(default_factory=list)
    warning_findings: list[ValidationFindingView] = field(default_factory=list)
    confirmation_findings: list[ValidationFindingView] = field(default_factory=list)
    informational_findings: list[ValidationFindingView] = field(default_factory=list)
    grouped_sections: list[ValidationGroupView] = field(default_factory=list)
    related_targets: list[ValidationTargetSummary] = field(default_factory=list)
    suggested_actions: list[ValidationActionHint] = field(default_factory=list)
    beginner_summary: BeginnerValidationSummaryView = field(default_factory=BeginnerValidationSummaryView)
    hide_raw_findings_by_default: bool = False
    filter_state: ValidationFilterState = field(default_factory=ValidationFilterState)
    explanation: str | None = None
    explainability: ExplainabilitySummaryView = field(default_factory=ExplainabilitySummaryView)


def _unwrap(source):
    if isinstance(source, LoadedNexArtifact):
        return source.parsed_model
    return source


def _storage_role(source) -> str:
    if source is None:
        return "none"
    if isinstance(source, WorkingSaveModel):
        return "working_save"
    if isinstance(source, CommitSnapshotModel):
        return "commit_snapshot"
    if isinstance(source, ExecutionRecordModel):
        return "execution_record"
    return "none"


def _target_type_from_location(location: str | None) -> tuple[str | None, str | None]:
    if not location:
        return None, None
    for prefix in ("node:", "edge:", "output:", "group:"):
        if location.startswith(prefix):
            return prefix[:-1], location.split(":", 1)[1]
    return "graph", None


def _from_validation_finding(finding: ValidationFinding, *, idx: int) -> ValidationFindingView:
    target_type, target_id = _target_type_from_location(finding.location)
    severity = "blocking" if finding.blocking else ("warning" if finding.severity in {"medium", "high"} else "info")
    return ValidationFindingView(
        finding_id=f"validation:{idx}:{finding.code}",
        severity=severity,
        category=finding.category,
        code=finding.code,
        title=finding.code.replace("_", " ").title(),
        message=finding.message,
        short_label=finding.hint,
        location_ref=finding.location,
        target_type=target_type,
        target_id=target_id,
        source_ref="validation_report",
        suggested_action=finding.hint,
        user_confirmation_allowed=False,
        auto_resolvable=False,
        destructive_risk=False,
    )


def _from_precheck_finding(finding: PrecheckFinding, severity: str, *, idx: int) -> ValidationFindingView:
    target_type, target_id = _target_type_from_location(finding.location)
    return ValidationFindingView(
        finding_id=f"precheck:{idx}:{finding.issue_code}",
        severity=severity,
        category="custom",
        code=finding.issue_code,
        title=finding.issue_code.replace("_", " ").title(),
        message=finding.message,
        short_label=finding.fix_hint,
        location_ref=finding.location,
        target_type=target_type,
        target_id=target_id,
        source_ref="designer_precheck",
        suggested_action=finding.fix_hint,
        user_confirmation_allowed=severity == "confirmation_required",
        auto_resolvable=False,
        destructive_risk=False,
    )




def _severity_from_verifier_status(status: str | None) -> str:
    if status == "fail":
        return "blocking"
    if status == "warning":
        return "warning"
    return "info"


def _from_verifier_artifact(artifact, *, idx: int, app_language: str) -> list[ValidationFindingView]:
    payload = artifact.payload_preview if isinstance(getattr(artifact, 'payload_preview', None), dict) else {}
    findings: list[ValidationFindingView] = []
    verifier_status = payload.get('aggregate_status') if isinstance(payload.get('aggregate_status'), str) else None
    constituent_results = payload.get('constituent_results') if isinstance(payload.get('constituent_results'), list) else []
    for result_index, result in enumerate(constituent_results, start=1):
        if not isinstance(result, dict):
            continue
        local_status = result.get('status') if isinstance(result.get('status'), str) else verifier_status
        local_severity = _severity_from_verifier_status(local_status)
        findings_list = result.get('findings') if isinstance(result.get('findings'), list) else []
        if findings_list:
            for finding_index, finding in enumerate(findings_list, start=1):
                if not isinstance(finding, dict):
                    continue
                findings.append(
                    ValidationFindingView(
                        finding_id=f"verifier:{idx}:{result_index}:{finding_index}",
                        severity=local_severity,
                        category=str(finding.get('category') or 'verification'),
                        code=str(finding.get('reason_code') or result.get('reason_code') or 'VERIFIER_FINDING'),
                        title=str((finding.get('message') or result.get('verifier_type') or 'Verifier finding')).split(':', 1)[0],
                        message=str(finding.get('message') or result.get('explanation') or 'Verifier finding'),
                        short_label=str(result.get('verifier_type') or artifact.artifact_type),
                        location_ref=str(result.get('target_ref') or artifact.producer_ref or '') or None,
                        target_type='node',
                        target_id=(artifact.producer_node or None),
                        source_ref=artifact.artifact_id,
                        suggested_action=(finding.get('suggested_action') if isinstance(finding.get('suggested_action'), str) else None),
                        user_confirmation_allowed=False,
                        auto_resolvable=False,
                        destructive_risk=False,
                    )
                )
        else:
            findings.append(
                ValidationFindingView(
                    finding_id=f"verifier:{idx}:{result_index}:aggregate",
                    severity=local_severity,
                    category=ui_text("validation.category.verification", app_language=app_language),
                    code=str(result.get('reason_code') or 'VERIFIER_RESULT'),
                    title=str(result.get('verifier_type') or ui_text('validation.title.verifier_report', app_language=app_language)).replace('_', ' ').title(),
                    message=str(result.get('explanation') or ui_text('validation.message.verifier_report_recorded', app_language=app_language)),
                    short_label=str(local_status or artifact.validation_status or 'verification'),
                    location_ref=str(result.get('target_ref') or artifact.producer_ref or '') or None,
                    target_type='node',
                    target_id=(artifact.producer_node or None),
                    source_ref=artifact.artifact_id,
                    suggested_action=None,
                    user_confirmation_allowed=False,
                    auto_resolvable=False,
                    destructive_risk=False,
                )
            )
    if findings:
        return findings
    summary_message = artifact.summary or 'Verifier report recorded'
    return [ValidationFindingView(
        finding_id=f"verifier:{idx}:summary",
        severity=_severity_from_verifier_status(verifier_status),
        category=ui_text("validation.category.verification", app_language=app_language),
        code='VERIFIER_REPORT',
        title=ui_text("validation.title.verifier_report", app_language=app_language),
        message=str(summary_message or ui_text("validation.message.verifier_report_recorded", app_language=app_language)),
        short_label=str(verifier_status or artifact.validation_status or 'verification'),
        location_ref=(artifact.producer_ref or None),
        target_type='node',
        target_id=(artifact.producer_node or None),
        source_ref=artifact.artifact_id,
        suggested_action=None,
        user_confirmation_allowed=False,
        auto_resolvable=False,
        destructive_risk=False,
    )]

def _from_execution_issue(issue: ExecutionIssue, severity: str, *, idx: int) -> ValidationFindingView:
    target_type, target_id = _target_type_from_location(issue.location)
    return ValidationFindingView(
        finding_id=f"execution:{idx}:{issue.issue_code}",
        severity=severity,
        category="execution_guard",
        code=issue.issue_code,
        title=issue.issue_code.replace("_", " ").title(),
        message=issue.message,
        short_label=issue.reason,
        location_ref=issue.location,
        target_type=target_type,
        target_id=target_id,
        source_ref="execution_record",
        suggested_action=issue.fix_hint,
        user_confirmation_allowed=False,
        auto_resolvable=False,
        destructive_risk=False,
    )


def _explainability_from_report(
    validation_report: ValidationReport | None,
    precheck: ValidationPrecheck | None,
    execution_record: ExecutionRecordModel | None,
) -> ExplainabilitySummaryView:
    """Build ExplainabilitySummaryView via policy_explainability.

    Constructs a synthetic PolicyDecision from available validation findings
    and passes it through build_explainability() to produce a structured
    explanation surface for the UI.
    """
    reasons: list[str] = []
    details: dict[str, object] = {}

    if validation_report is not None:
        for f in (validation_report.findings or []):
            rule = getattr(f, "rule_id", None) or getattr(f, "code", None) or "unknown"
            severity = getattr(f, "severity", "warning")
            message = getattr(f, "message", "") or str(f)
            reasons.append(f"[{severity}] {rule}: {message}")

    if precheck is not None:
        for f in (precheck.blocking_findings or []):
            reasons.append(f"[blocking] {getattr(f, 'rule_id', 'rule')}: {getattr(f, 'message', '')}")
        for f in (precheck.warning_findings or []):
            reasons.append(f"[warning] {getattr(f, 'rule_id', 'rule')}: {getattr(f, 'message', '')}")

    if execution_record is not None:
        for issue in (execution_record.diagnostics.errors or []):
            reasons.append(f"[error] {getattr(issue, 'code', 'execution_error')}: {getattr(issue, 'message', '')}")

    if not reasons and validation_report is None and precheck is None and execution_record is None:
        return ExplainabilitySummaryView()

    # Derive status from available data
    if validation_report is not None:
        raw_status = validation_report.result or "unknown"
        policy_status = "PASS" if raw_status in {"passed", "pass"} else "FAIL"
    elif precheck is not None:
        policy_status = "PASS" if precheck.overall_status in {"pass", "pass_with_warnings"} else "FAIL"
    else:
        policy_status = "PASS" if not reasons else "FAIL"

    decision = PolicyDecision(status=policy_status, reasons=reasons, details=details)
    result: ExplainabilityResult = build_explainability(decision)

    return ExplainabilitySummaryView(
        status=result.status,
        summary=result.summary,
        structural_issues=list(result.categories.get("structural", [])),
        semantic_issues=list(result.categories.get("semantic", [])),
        verification_contracts=list(result.verification_contracts),
        has_explainability=True,
    )


def _governance_summary_from_sources(source, execution_record: ExecutionRecordModel | None) -> dict[str, object]:
    if execution_record is not None:
        metrics = execution_record.observability.metrics if isinstance(execution_record.observability.metrics, dict) else {}
        governance = metrics.get("governance") if isinstance(metrics.get("governance"), dict) else None
        recovery = metrics.get("recovery") if isinstance(metrics.get("recovery"), dict) else None
        policy_validation = recovery.get("policy_validation") if isinstance(recovery, dict) and isinstance(recovery.get("policy_validation"), dict) else None
        if governance is not None or policy_validation is not None:
            projected = dict(governance) if governance is not None else {}
            if policy_validation is not None:
                projected["policy_validation"] = dict(policy_validation)
            return projected
    if isinstance(source, WorkingSaveModel):
        last_run = source.runtime.last_run if isinstance(source.runtime.last_run, dict) else {}
        governance = last_run.get("governance") if isinstance(last_run.get("governance"), dict) else None
        policy_validation = last_run.get("policy_validation") if isinstance(last_run.get("policy_validation"), dict) else None
        if governance is not None or policy_validation is not None:
            projected = dict(governance) if governance is not None else {}
            if policy_validation is not None:
                projected["policy_validation"] = dict(policy_validation)
            if governance is not None:
                return projected
        projected: dict[str, object] = {}
        for key in (
            "launch_status",
            "safety_status",
            "safety_reason_code",
            "quota_status",
            "quota_reason_code",
            "delivery_status",
            "delivery_reason_code",
            "delivery_destination_ref",
            "reason_codes",
            "top_reason_code",
        ):
            value = last_run.get(key)
            if value is not None and value != "" and value != []:
                projected[key] = value
        if policy_validation is not None:
            projected["policy_validation"] = dict(policy_validation)
        return projected
    return {}

def _severity_for_governance_status(status: str, *, family: str) -> str:
    lowered = status.lower()
    if family == "delivery" and lowered in {"failed", "blocked"}:
        return "warning"
    if "blocked" in lowered:
        return "blocking"
    if "confirmation" in lowered:
        return "confirmation_required"
    if "warning" in lowered or "near" in lowered:
        return "warning"
    return "info"


def _governance_findings(summary: dict[str, object], *, app_language: str) -> list[ValidationFindingView]:
    findings: list[ValidationFindingView] = []
    family_to_reason = {
        "launch": "launch_reason_code",
        "safety": "safety_reason_code",
        "quota": "quota_reason_code",
        "delivery": "delivery_reason_code",
        "streaming": "streaming_reason_code",
    }
    specific_status_present = any(
        isinstance(summary.get(key), str) and summary.get(key)
        for key in ("safety_status", "quota_status", "delivery_status", "streaming_status")
    )
    index = 1
    for family in ("launch", "safety", "quota", "delivery", "streaming"):
        if family == "launch" and specific_status_present:
            continue
        status = summary.get(f"{family}_status")
        if not isinstance(status, str) or not status or status in {"allowed", "safe", "within_limit", "succeeded", "completed", "available", "not_attempted"}:
            continue
        reason_code = summary.get(family_to_reason[family]) if isinstance(summary.get(family_to_reason[family]), str) else None
        record = lookup_reason_code_record(reason_code) if reason_code else None
        findings.append(
            ValidationFindingView(
                finding_id=f"governance:{index}:{family}",
                severity=_severity_for_governance_status(status, family=family),
                category="governance",
                code=reason_code or f"{family}.{status}",
                title=f"{family.title()} {status.replace('_', ' ').title()}",
                message=(record.human_summary if record is not None else f"{family.title()} status is {status.replace('_', ' ')}."),
                short_label=status.replace("_", " "),
                location_ref=None,
                target_type="graph",
                target_id=None,
                source_ref="governance_summary",
                suggested_action=(record.recommended_next_action if record is not None else None),
                user_confirmation_allowed=(status == "confirmation_required"),
                auto_resolvable=False,
                destructive_risk=False,
            )
        )
        index += 1

    policy_validation = summary.get("policy_validation") if isinstance(summary.get("policy_validation"), dict) else None
    if policy_validation is not None:
        status = str(policy_validation.get("status") or "invalid")
        reason = str(policy_validation.get("reason") or "invalid_policy")
        fallback_applied = bool(policy_validation.get("fallback_applied"))
        findings.append(
            ValidationFindingView(
                finding_id=f"governance:{index}:policy_validation",
                severity="warning",
                category="governance",
                code=reason,
                title=ui_text(
                    "validation.title.policy_validation",
                    app_language=app_language,
                    fallback_text="Policy validation",
                ),
                message=ui_text(
                    "validation.message.policy_validation",
                    app_language=app_language,
                    fallback_text=(
                        "Fallback scoring policy was invalid ({reason}). Safe defaults were applied."
                        if fallback_applied
                        else "Fallback scoring policy was invalid ({reason})."
                    ),
                    reason=reason,
                ),
                short_label=status.replace("_", " "),
                location_ref=None,
                target_type="graph",
                target_id=None,
                source_ref="governance_summary",
                suggested_action=ui_text(
                    "validation.action.review_policy",
                    app_language=app_language,
                    fallback_text="Review policy configuration",
                ),
                user_confirmation_allowed=False,
                auto_resolvable=False,
                destructive_risk=False,
            )
        )
    return findings

def _group_by_severity(all_findings: list[ValidationFindingView], *, app_language: str) -> list[ValidationGroupView]:
    groups: list[ValidationGroupView] = []
    for severity in ("blocking", "warning", "confirmation_required", "info"):
        findings = [finding for finding in all_findings if finding.severity == severity]
        if findings:
            groups.append(
                ValidationGroupView(
                    group_id=f"severity:{severity}",
                    group_label=ui_text(f"validation.group.{severity}", app_language=app_language, fallback_text=severity.replace("_", " ").title()),
                    group_type="severity",
                    findings=findings,
                    count=len(findings),
                    collapsed_by_default=severity in {"info"},
                )
            )
    return groups




def _beginner_status_signal(overall_status: str, *, app_language: str) -> str:
    if overall_status == "blocked":
        key = "validation.beginner.status.blocked"
    elif overall_status in {"confirmation_required", "pass_with_warnings"}:
        key = "validation.beginner.status.confirmation_required"
    else:
        key = "validation.beginner.status.ready"
    return ui_text(key, app_language=app_language)


def _beginner_next_action(*, overall_status: str, source_mode: str, app_language: str) -> tuple[str | None, str | None]:
    if overall_status == "blocked":
        return "focus_top_issue", ui_text("validation.beginner.action.fix_issue", app_language=app_language)
    if overall_status in {"confirmation_required", "pass_with_warnings"}:
        action_type = "proceed_to_approval" if source_mode == "designer_precheck" else "request_revision"
        return action_type, ui_text("validation.beginner.action.review_change", app_language=app_language)
    return "run", ui_text("validation.beginner.action.run", app_language=app_language)


def _beginner_summary(
    *,
    source,
    execution_record: ExecutionRecordModel | None,
    overall_status: str,
    source_mode: str,
    all_findings: list[ValidationFindingView],
    app_language: str,
) -> BeginnerValidationSummaryView:
    if not beginner_language_enabled(source, execution_record):
        return BeginnerValidationSummaryView()
    top_finding = all_findings[0] if all_findings else None
    cause = top_finding.message if top_finding is not None else ui_text("validation.beginner.cause.ready", app_language=app_language)
    action_type, action_label = _beginner_next_action(overall_status=overall_status, source_mode=source_mode, app_language=app_language)
    return BeginnerValidationSummaryView(
        status_signal=_beginner_status_signal(overall_status, app_language=app_language),
        cause=cause,
        next_action_type=action_type,
        next_action_label=action_label,
    )

def _target_summaries(all_findings: list[ValidationFindingView], *, app_language: str) -> list[ValidationTargetSummary]:
    by_target: dict[tuple[str, str | None], list[ValidationFindingView]] = {}
    for finding in all_findings:
        key = (finding.target_type or "graph", finding.target_id)
        by_target.setdefault(key, []).append(finding)
    summaries: list[ValidationTargetSummary] = []
    for (target_type, target_id), findings in by_target.items():
        summaries.append(
            ValidationTargetSummary(
                target_type=target_type,
                target_id=target_id,
                finding_count=len(findings),
                blocking_count=sum(1 for finding in findings if finding.severity == "blocking"),
                warning_count=sum(1 for finding in findings if finding.severity == "warning"),
                confirmation_count=sum(1 for finding in findings if finding.severity == "confirmation_required"),
                label=target_id or (ui_text("validation.target.graph", app_language=app_language) if target_type == "graph" else target_type),
            )
        )
    return sorted(summaries, key=lambda item: (-item.blocking_count, -item.finding_count, item.label or ""))




def _friendly_error_for_validation(
    *,
    validation_report: ValidationReport | None,
    precheck: ValidationPrecheck | None,
    execution_record: ExecutionRecordModel | None,
    governance_summary: dict[str, Any],
    app_language: str,
) -> FriendlyErrorView:
    candidates: list[dict[str, Any]] = []

    if validation_report is not None:
        for finding in validation_report.findings:
            candidates.append({
                "source_kind": "validation",
                "issue_code": finding.code,
                "message": finding.message,
            })

    if precheck is not None:
        for group in (precheck.blocking_findings, precheck.warning_findings, precheck.confirmation_findings):
            for finding in group:
                candidates.append({
                    "source_kind": "precheck",
                    "issue_code": finding.issue_code,
                    "message": finding.message,
                })

    if execution_record is not None:
        for issue in [*execution_record.diagnostics.errors, *execution_record.diagnostics.warnings]:
            candidates.append({
                "source_kind": issue.category,
                "issue_code": issue.issue_code,
                "message": issue.message or issue.reason or issue.fix_hint,
            })

    for family_prefix in ("launch", "safety", "quota", "delivery", "streaming"):
        reason_key = f"{family_prefix}_reason_code"
        status_key = f"{family_prefix}_status"
        if isinstance(governance_summary.get(reason_key), str):
            candidates.append({
                "source_kind": family_prefix,
                "reason_code": governance_summary.get(reason_key),
                "issue_code": governance_summary.get(status_key),
            })

    policy_validation = governance_summary.get("policy_validation") if isinstance(governance_summary.get("policy_validation"), dict) else None
    if policy_validation is not None:
        candidates.append({
            "source_kind": "policy_validation",
            "reason_code": policy_validation.get("reason") if isinstance(policy_validation.get("reason"), str) else None,
            "issue_code": policy_validation.get("status") if isinstance(policy_validation.get("status"), str) else None,
            "message": (
                f"Fallback scoring policy was invalid ({policy_validation.get('reason')})."
                if isinstance(policy_validation.get("reason"), str)
                else "Fallback scoring policy was invalid."
            ),
        })

    return friendly_error_from_candidates(app_language=app_language, candidates=candidates)
def read_validation_panel_view_model(
    source: WorkingSaveModel | CommitSnapshotModel | ExecutionRecordModel | LoadedNexArtifact | None,
    *,
    validation_report: ValidationReport | None = None,
    precheck: ValidationPrecheck | None = None,
    execution_record: ExecutionRecordModel | None = None,
    explanation: str | None = None,
) -> ValidationPanelViewModel:
    source = _unwrap(source)
    app_language = ui_language_from_sources(source, execution_record)
    storage_role = _storage_role(source)
    blocking_findings: list[ValidationFindingView] = []
    warning_findings: list[ValidationFindingView] = []
    confirmation_findings: list[ValidationFindingView] = []
    informational_findings: list[ValidationFindingView] = []
    source_mode = "unknown"
    overall_status = "unknown"
    governance_summary = _governance_summary_from_sources(source, execution_record)

    if precheck is not None:
        source_mode = "designer_precheck"
        mapping = {
            "pass": "pass",
            "pass_with_warnings": "pass_with_warnings",
            "confirmation_required": "confirmation_required",
            "blocked": "blocked",
        }
        overall_status = mapping.get(precheck.overall_status, "unknown")
        blocking_findings = [_from_precheck_finding(finding, "blocking", idx=i) for i, finding in enumerate(precheck.blocking_findings, start=1)]
        warning_findings = [_from_precheck_finding(finding, "warning", idx=i) for i, finding in enumerate(precheck.warning_findings, start=1)]
        confirmation_findings = [_from_precheck_finding(finding, "confirmation_required", idx=i) for i, finding in enumerate(precheck.confirmation_findings, start=1)]
    elif validation_report is not None:
        source_mode = f"{validation_report.role}_validation"
        overall_status = {
            "passed": "pass",
            "passed_with_findings": "pass_with_warnings",
            "failed": "blocked",
            "blocked": "blocked",
        }.get(validation_report.result, "unknown")
        converted = [_from_validation_finding(finding, idx=i) for i, finding in enumerate(validation_report.findings, start=1)]
        blocking_findings = [finding for finding in converted if finding.severity == "blocking"]
        warning_findings = [finding for finding in converted if finding.severity == "warning"]
        informational_findings = [finding for finding in converted if finding.severity == "info"]
    elif execution_record is not None:
        source_mode = "execution_guard"
        blocking_findings = [_from_execution_issue(issue, "blocking", idx=i) for i, issue in enumerate(execution_record.diagnostics.errors, start=1)]
        warning_findings = [_from_execution_issue(issue, "warning", idx=i) for i, issue in enumerate(execution_record.diagnostics.warnings, start=1)]
        verifier_findings: list[ValidationFindingView] = []
        for i, artifact in enumerate(execution_record.artifacts.artifact_refs, start=1):
            if artifact.artifact_type == 'validation_report':
                verifier_findings.extend(_from_verifier_artifact(artifact, idx=i, app_language=app_language))
        blocking_findings.extend([finding for finding in verifier_findings if finding.severity == 'blocking'])
        warning_findings.extend([finding for finding in verifier_findings if finding.severity == 'warning'])
        informational_findings.extend([finding for finding in verifier_findings if finding.severity == 'info'])
        governance_findings = _governance_findings(governance_summary, app_language=app_language)
        blocking_findings.extend([finding for finding in governance_findings if finding.severity == 'blocking'])
        warning_findings.extend([finding for finding in governance_findings if finding.severity == 'warning'])
        confirmation_findings.extend([finding for finding in governance_findings if finding.severity == 'confirmation_required'])
        informational_findings.extend([finding for finding in governance_findings if finding.severity == 'info'])
        overall_status = "blocked" if blocking_findings else ("confirmation_required" if confirmation_findings else ("pass_with_warnings" if warning_findings else "pass"))

    if source_mode == "unknown" and governance_summary:
        source_mode = "governance_summary"
        governance_findings = _governance_findings(governance_summary, app_language=app_language)
        blocking_findings.extend([finding for finding in governance_findings if finding.severity == 'blocking'])
        warning_findings.extend([finding for finding in governance_findings if finding.severity == 'warning'])
        confirmation_findings.extend([finding for finding in governance_findings if finding.severity == 'confirmation_required'])
        informational_findings.extend([finding for finding in governance_findings if finding.severity == 'info'])
        overall_status = "blocked" if blocking_findings else ("confirmation_required" if confirmation_findings else ("pass_with_warnings" if warning_findings else "pass"))

    beginner_mode = beginner_language_enabled(source, execution_record)
    all_findings = [*blocking_findings, *warning_findings, *confirmation_findings, *informational_findings]
    related_targets = _target_summaries(all_findings, app_language=app_language)
    friendly_error = _friendly_error_for_validation(
        validation_report=validation_report,
        precheck=precheck,
        execution_record=execution_record,
        governance_summary=governance_summary,
        app_language=app_language,
    )
    summary = ValidationSummaryView(
        blocking_count=len(blocking_findings),
        warning_count=len(warning_findings),
        confirmation_count=len(confirmation_findings),
        info_count=len(informational_findings),
        affected_node_count=sum(1 for item in related_targets if item.target_type == "node"),
        affected_edge_count=sum(1 for item in related_targets if item.target_type == "edge"),
        affected_output_count=sum(1 for item in related_targets if item.target_type == "output"),
        affected_group_count=sum(1 for item in related_targets if item.target_type == "group"),
        top_issue_label=(all_findings[0].title if all_findings else None),
        can_commit=source_mode not in {"execution_guard"} and overall_status in {"pass", "pass_with_warnings"},
        can_execute=source_mode not in {"designer_precheck", "execution_guard"} and not blocking_findings,
        requires_user_confirmation=bool(confirmation_findings),
    )
    if source_mode == "execution_guard":
        trace_available = bool(execution_record is not None and (execution_record.timeline.trace_ref or execution_record.timeline.event_stream_ref or (execution_record.timeline.event_count or 0) > 0))
        artifact_available = bool(execution_record is not None and ((execution_record.artifacts.artifact_count or 0) > 0 or len(execution_record.artifacts.artifact_refs) > 0))
        suggested_actions = [
            ValidationActionHint("focus_top_issue", ui_text("validation.action.focus_top_issue", app_language=app_language), bool(all_findings), None if all_findings else ui_text("validation.reason.no_findings", app_language=app_language)),
            ValidationActionHint(
                "open_trace",
                ui_text("validation.action.open_trace", app_language=app_language),
                trace_available,
                None if trace_available else ui_text("validation.reason.no_trace", app_language=app_language),
            ),
            ValidationActionHint(
                "open_artifacts",
                ui_text("validation.action.open_artifacts", app_language=app_language),
                artifact_available,
                None if artifact_available else ui_text("validation.reason.no_artifacts", app_language=app_language),
            ),
        ]
    else:
        suggested_actions = [
            ValidationActionHint("focus_top_issue", ui_text("validation.action.focus_top_issue", app_language=app_language), bool(all_findings), None if all_findings else ui_text("validation.reason.no_findings", app_language=app_language)),
            ValidationActionHint(
                "request_revision",
                ui_text("validation.action.request_revision", app_language=app_language),
                overall_status in {"blocked", "confirmation_required", "pass_with_warnings"},
                None if overall_status in {"blocked", "confirmation_required", "pass_with_warnings"} else ui_text("validation.reason.no_revision_required", app_language=app_language),
            ),
            ValidationActionHint(
                "proceed_to_approval",
                ui_text("validation.action.proceed_to_approval", app_language=app_language),
                overall_status in {"pass", "pass_with_warnings"} and not blocking_findings,
                None if overall_status in {"pass", "pass_with_warnings"} and not blocking_findings else ui_text("validation.reason.blocking_issues_remain", app_language=app_language),
            ),
        ]
    return ValidationPanelViewModel(
        source_mode=source_mode,
        storage_role=storage_role,
        overall_status=overall_status,
        friendly_error=friendly_error,
        beginner_mode=beginner_mode,
        summary=summary,
        blocking_findings=blocking_findings,
        warning_findings=warning_findings,
        confirmation_findings=confirmation_findings,
        informational_findings=informational_findings,
        grouped_sections=_group_by_severity(all_findings, app_language=app_language),
        related_targets=related_targets,
        suggested_actions=suggested_actions,
        beginner_summary=_beginner_summary(source=source, execution_record=execution_record, overall_status=overall_status, source_mode=source_mode, all_findings=all_findings, app_language=app_language),
        hide_raw_findings_by_default=beginner_mode,
        explanation=explanation,
        explainability=_explainability_from_report(validation_report, precheck, execution_record),
    )


__all__ = [
    "BeginnerValidationSummaryView",
    "ValidationActionHint",
    "ValidationFilterState",
    "ValidationFindingView",
    "ValidationGroupView",
    "ValidationPanelViewModel",
    "ValidationSummaryView",
    "ValidationTargetSummary",
    "read_validation_panel_view_model",
]
