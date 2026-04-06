from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.validation_precheck import ValidationPrecheck, PrecheckFinding
from src.storage.models.execution_record_model import ExecutionIssue, ExecutionRecordModel
from src.storage.models.loaded_nex_artifact import LoadedNexArtifact
from src.storage.models.commit_snapshot_model import CommitSnapshotModel
from src.storage.models.working_save_model import WorkingSaveModel


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


def _group_by_severity(all_findings: list[ValidationFindingView]) -> list[ValidationGroupView]:
    groups: list[ValidationGroupView] = []
    for severity in ("blocking", "warning", "confirmation_required", "info"):
        findings = [finding for finding in all_findings if finding.severity == severity]
        if findings:
            groups.append(
                ValidationGroupView(
                    group_id=f"severity:{severity}",
                    group_label=severity.replace("_", " ").title(),
                    group_type="severity",
                    findings=findings,
                    count=len(findings),
                    collapsed_by_default=severity in {"info"},
                )
            )
    return groups


def _target_summaries(all_findings: list[ValidationFindingView]) -> list[ValidationTargetSummary]:
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
                label=target_id or target_type,
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
    storage_role = _storage_role(source)
    blocking_findings: list[ValidationFindingView] = []
    warning_findings: list[ValidationFindingView] = []
    confirmation_findings: list[ValidationFindingView] = []
    informational_findings: list[ValidationFindingView] = []
    source_mode = "unknown"
    overall_status = "unknown"

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
        }.get(validation_report.result, "unknown")
        converted = [_from_validation_finding(finding, idx=i) for i, finding in enumerate(validation_report.findings, start=1)]
        blocking_findings = [finding for finding in converted if finding.severity == "blocking"]
        warning_findings = [finding for finding in converted if finding.severity == "warning"]
        informational_findings = [finding for finding in converted if finding.severity == "info"]
    elif execution_record is not None:
        source_mode = "execution_guard"
        overall_status = "blocked" if execution_record.diagnostics.errors else ("pass_with_warnings" if execution_record.diagnostics.warnings else "pass")
        blocking_findings = [_from_execution_issue(issue, "blocking", idx=i) for i, issue in enumerate(execution_record.diagnostics.errors, start=1)]
        warning_findings = [_from_execution_issue(issue, "warning", idx=i) for i, issue in enumerate(execution_record.diagnostics.warnings, start=1)]

    all_findings = [*blocking_findings, *warning_findings, *confirmation_findings, *informational_findings]
    related_targets = _target_summaries(all_findings)
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
        can_commit=overall_status in {"pass", "pass_with_warnings"},
        can_execute=source_mode != "designer_precheck" and not blocking_findings,
        requires_user_confirmation=bool(confirmation_findings),
    )
    suggested_actions = [
        ValidationActionHint("focus_top_issue", "Focus top issue", bool(all_findings), None if all_findings else "No findings available"),
        ValidationActionHint(
            "request_revision",
            "Request revision",
            overall_status in {"blocked", "confirmation_required", "pass_with_warnings"},
            None if overall_status in {"blocked", "confirmation_required", "pass_with_warnings"} else "No revision required",
        ),
        ValidationActionHint(
            "proceed_to_approval",
            "Proceed to approval",
            overall_status in {"pass", "pass_with_warnings"} and not blocking_findings,
            None if overall_status in {"pass", "pass_with_warnings"} and not blocking_findings else "Blocking issues remain",
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
        grouped_sections=_group_by_severity(all_findings),
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
