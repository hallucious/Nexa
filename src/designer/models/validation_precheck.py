from __future__ import annotations

from dataclasses import dataclass, field

from src.contracts.designer_contract import CHANGE_SCOPE_LEVELS, PRECHECK_OVERALL_STATUSES


@dataclass(frozen=True)
class EvaluatedScope:
    mode: str
    savefile_ref: str | None = None
    touched_nodes: tuple[str, ...] = ()
    touched_edges: tuple[str, ...] = ()
    touched_outputs: tuple[str, ...] = ()
    touch_summary: str = ""

    def __post_init__(self) -> None:
        allowed = {"new_circuit", "existing_circuit_patch", "subgraph_patch", "node_patch"}
        if self.mode not in allowed:
            raise ValueError(f"Unsupported evaluated scope mode: {self.mode}")


@dataclass(frozen=True)
class PrecheckFinding:
    issue_code: str
    message: str
    severity: str = "medium"
    location: str | None = None
    fix_hint: str | None = None

    def __post_init__(self) -> None:
        if not self.issue_code.strip():
            raise ValueError("PrecheckFinding.issue_code must be non-empty")
        if not self.message.strip():
            raise ValueError("PrecheckFinding.message must be non-empty")
        if self.severity not in {"low", "medium", "high"}:
            raise ValueError(f"Unsupported precheck finding severity: {self.severity}")


@dataclass(frozen=True)
class ValidityReport:
    status: str
    summary: str = ""
    findings: tuple[PrecheckFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"valid", "warning", "blocked", "unresolved", "unknown"}:
            raise ValueError(f"Unsupported validity report status: {self.status}")


@dataclass(frozen=True)
class ResolutionReport:
    status: str
    summary: str = ""
    missing_refs: tuple[str, ...] = ()
    findings: tuple[PrecheckFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"resolved", "warning", "blocked", "unknown"}:
            raise ValueError(f"Unsupported resolution report status: {self.status}")


@dataclass(frozen=True)
class CostAssessmentReport:
    status: str
    summary: str = ""
    estimated_cost_impact: str | None = None
    findings: tuple[PrecheckFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"acceptable", "warning", "blocked", "unknown"}:
            raise ValueError(f"Unsupported cost assessment status: {self.status}")


@dataclass(frozen=True)
class AmbiguityAssessmentReport:
    status: str
    summary: str = ""
    findings: tuple[PrecheckFinding, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"clear", "warning", "confirmation_required", "blocked", "unknown"}:
            raise ValueError(f"Unsupported ambiguity assessment status: {self.status}")


@dataclass(frozen=True)
class PreviewRequirements:
    required_sections: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationPrecheck:
    precheck_id: str
    patch_ref: str
    intent_ref: str
    evaluated_scope: EvaluatedScope
    overall_status: str
    structural_validity: ValidityReport = field(default_factory=lambda: ValidityReport(status="unknown"))
    dependency_validity: ValidityReport = field(default_factory=lambda: ValidityReport(status="unknown"))
    input_output_validity: ValidityReport = field(default_factory=lambda: ValidityReport(status="unknown"))
    provider_resolution: ResolutionReport = field(default_factory=lambda: ResolutionReport(status="unknown"))
    plugin_resolution: ResolutionReport = field(default_factory=lambda: ResolutionReport(status="unknown"))
    safety_review: ValidityReport = field(default_factory=lambda: ValidityReport(status="unknown"))
    cost_assessment: CostAssessmentReport = field(default_factory=lambda: CostAssessmentReport(status="unknown"))
    ambiguity_assessment: AmbiguityAssessmentReport = field(default_factory=lambda: AmbiguityAssessmentReport(status="unknown"))
    preview_requirements: PreviewRequirements = field(default_factory=PreviewRequirements)
    blocking_findings: tuple[PrecheckFinding, ...] = ()
    warning_findings: tuple[PrecheckFinding, ...] = ()
    confirmation_findings: tuple[PrecheckFinding, ...] = ()
    recommended_next_actions: tuple[str, ...] = ()
    explanation: str = ""

    def __post_init__(self) -> None:
        if not self.precheck_id.strip():
            raise ValueError("ValidationPrecheck.precheck_id must be non-empty")
        if not self.patch_ref.strip():
            raise ValueError("ValidationPrecheck.patch_ref must be non-empty")
        if not self.intent_ref.strip():
            raise ValueError("ValidationPrecheck.intent_ref must be non-empty")
        if self.overall_status not in PRECHECK_OVERALL_STATUSES:
            raise ValueError(f"Unsupported ValidationPrecheck.overall_status: {self.overall_status}")
        if self.overall_status == "blocked" and not self.blocking_findings:
            raise ValueError("ValidationPrecheck.blocking_findings must be present when overall_status is 'blocked'")
        if self.overall_status == "confirmation_required" and not self.confirmation_findings:
            raise ValueError(
                "ValidationPrecheck.confirmation_findings must be present when overall_status is 'confirmation_required'"
            )
        if self.blocking_findings and self.overall_status != "blocked":
            raise ValueError("ValidationPrecheck.overall_status must be 'blocked' when blocking_findings are present")

    @property
    def blocking_finding_count(self) -> int:
        return len(self.blocking_findings)

    @property
    def warning_finding_count(self) -> int:
        return len(self.warning_findings)

    @property
    def confirmation_finding_count(self) -> int:
        return len(self.confirmation_findings)

    @property
    def can_proceed_to_preview(self) -> bool:
        return self.overall_status != "blocked" and not self.blocking_findings
