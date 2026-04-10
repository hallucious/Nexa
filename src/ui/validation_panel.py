from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.validation_precheck import ValidationPrecheck, PrecheckFinding
from src.storage.models.execution_record_model import ExecutionIssue, ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.working_save_model import WorkingSaveModel
from src.contracts.status_taxonomy import lookup_reason_code_record
from src.ui.i18n import ui_language_from_sources, ui_text


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
class ValidationPanelViewModel:
    source_mode: str
    storage_role: str
    overall_status: str
    summary: ValidationSummaryView = field(default_factory=ValidationSummaryView)
    blocking_findings: list[ValidationFindingView] = field(default_factory=list)
    warning_findings: list[ValidationFindingView] = field(default_factory=list)
    confirmation_findings: list[ValidationFindingView] = field(default_factory=list)
    informational_findings: list[ValidationFindingView] = field(default_factory=list)
    grouped_sections: list[ValidationGroupView] = field(default_factory=list)
    related_targets: list[ValidationTargetSummary] = field(default_factory=list)
    suggested_actions: list[ValidationActionHint] = field(default_factory=list)
    filter_state: ValidationFilterState = field(default_factory=ValidationFilterState)
    explanation: str | None = None


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


def _governance_summary_from_sources(source, execution_record: ExecutionRecordModel | None) -> dict[str, object]:
    if execution_record is not None:
        metrics = execution_record.observability.metrics if isinstance(execution_record.observability.metrics, dict) else {}
        governance = metrics.get("governance") if isinstance(metrics.get("governance"), dict) else None
        if governance is not None:
            return dict(governance)
    if isinstance(source, WorkingSaveModel):
        last_run = source.runtime.last_run if isinstance(source.runtime.last_run, dict) else {}
        governance = last_run.get("governance") if isinstance(last_run.get("governance"), dict) else None
        if governance is not None:
            return dict(governance)
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

    all_findings = [*blocking_findings, *warning_findings, *confirmation_findings, *informational_findings]
    related_targets = _target_summaries(all_findings, app_language=app_language)
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
        summary=summary,
        blocking_findings=blocking_findings,
        warning_findings=warning_findings,
        confirmation_findings=confirmation_findings,
        informational_findings=informational_findings,
        grouped_sections=_group_by_severity(all_findings, app_language=app_language),
        related_targets=related_targets,
        suggested_actions=suggested_actions,
        explanation=explanation,
    )


__all__ = [
    "ValidationActionHint",
    "ValidationFilterState",
    "ValidationFindingView",
    "ValidationGroupView",
    "ValidationPanelViewModel",
    "ValidationSummaryView",
    "ValidationTargetSummary",
    "read_validation_panel_view_model",
]
