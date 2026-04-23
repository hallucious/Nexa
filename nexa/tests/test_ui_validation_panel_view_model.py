from __future__ import annotations

from dataclasses import replace

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.validation_precheck import (
    AmbiguityAssessmentReport,
    CostAssessmentReport,
    EvaluatedScope,
    PrecheckFinding,
    PreviewRequirements,
    ResolutionReport,
    ValidationPrecheck,
    ValidityReport,
)
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionIssue, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.validation_panel import read_validation_panel_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "review_bundle"}], edges=[], entry="review_bundle", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _validation_report() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[
            ValidationFinding(code="MISSING_INPUT", category="structural", severity="high", blocking=True, location="node:review_bundle", message="input missing"),
            ValidationFinding(code="WEAK_LABEL", category="semantic", severity="low", blocking=False, location="node:review_bundle", message="label is weak"),
        ],
        blocking_count=1,
        warning_count=1,
        result="failed",
    )


def _precheck() -> ValidationPrecheck:
    return ValidationPrecheck(
        precheck_id="pre-001",
        patch_ref="patch-001",
        intent_ref="intent-001",
        evaluated_scope=EvaluatedScope(mode="existing_circuit_patch", touched_nodes=("review_bundle",)),
        overall_status="confirmation_required",
        structural_validity=ValidityReport(status="valid"),
        dependency_validity=ValidityReport(status="warning"),
        input_output_validity=ValidityReport(status="valid"),
        provider_resolution=ResolutionReport(status="resolved"),
        plugin_resolution=ResolutionReport(status="resolved"),
        safety_review=ValidityReport(status="warning"),
        cost_assessment=CostAssessmentReport(status="warning"),
        ambiguity_assessment=AmbiguityAssessmentReport(status="warning"),
        preview_requirements=PreviewRequirements(required_sections=("summary",)),
        confirmation_findings=(PrecheckFinding(issue_code="CONFIRM_PROVIDER", location="node:review_bundle", message="provider replacement changes semantics", fix_hint="Confirm provider replacement"),),
        recommended_next_actions=("Get user confirmation",),
        explanation="needs explicit confirmation",
    )


def _execution_record() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-07T00:00:00Z", started_at="2026-04-07T00:00:00Z", finished_at="2026-04-07T00:00:05Z", status="failed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(errors=[ExecutionIssue(issue_code="RUNTIME_ERROR", category="runtime", severity="high", location="node:review_bundle", message="run failed")], warnings=[]),
        observability=ExecutionObservabilityModel(),
    )


def test_read_validation_panel_view_model_projects_working_save_validation() -> None:
    vm = read_validation_panel_view_model(_working_save(), validation_report=_validation_report())
    assert vm.source_mode == "working_save_validation"
    assert vm.overall_status == "blocked"
    assert vm.summary.blocking_count == 1
    assert vm.related_targets[0].target_type == "node"


def test_read_validation_panel_view_model_projects_designer_precheck() -> None:
    vm = read_validation_panel_view_model(_working_save(), precheck=_precheck())
    assert vm.source_mode == "designer_precheck"
    assert vm.overall_status == "confirmation_required"
    assert vm.summary.requires_user_confirmation is True
    assert vm.confirmation_findings[0].user_confirmation_allowed is True


def test_read_validation_panel_view_model_projects_execution_guard() -> None:
    vm = read_validation_panel_view_model(_working_save(), execution_record=_execution_record())
    assert vm.source_mode == "execution_guard"
    assert vm.overall_status == "blocked"
    assert vm.blocking_findings[0].code == "RUNTIME_ERROR"


def test_validation_panel_projects_execution_guard_as_history_review_actions() -> None:
    vm = read_validation_panel_view_model(_working_save(), execution_record=_execution_record())

    assert vm.source_mode == "execution_guard"
    assert vm.summary.can_commit is False
    assert vm.summary.can_execute is False
    assert [action.action_type for action in vm.suggested_actions] == ["focus_top_issue", "open_trace", "open_artifacts"]
    assert vm.suggested_actions[1].enabled is False
    assert vm.suggested_actions[2].enabled is False



def test_validation_panel_compresses_beginner_blocked_message() -> None:
    vm = read_validation_panel_view_model(_working_save(), validation_report=_validation_report())

    assert vm.beginner_mode is True
    assert vm.hide_raw_findings_by_default is True
    assert vm.beginner_summary.status_signal == "Cannot run yet."
    assert vm.beginner_summary.cause == "input missing"
    assert vm.beginner_summary.next_action_type == "focus_top_issue"
    assert vm.beginner_summary.next_action_label == "Fix this step"


def test_validation_panel_compresses_beginner_ready_message() -> None:
    ready_report = ValidationReport(role="working_save", findings=[], blocking_count=0, warning_count=0, result="passed")

    vm = read_validation_panel_view_model(_working_save(), validation_report=ready_report)

    assert vm.beginner_mode is True
    assert vm.beginner_summary.status_signal == "Ready to run."
    assert vm.beginner_summary.cause == "Everything needed to run is ready."
    assert vm.beginner_summary.next_action_type == "run"
    assert vm.beginner_summary.next_action_label == "Run"


def test_validation_panel_surfaces_policy_validation_warning_from_working_save_last_run() -> None:
    base = _working_save()
    source = replace(base, runtime=replace(base.runtime, last_run={
        "policy_validation": {
            "status": "invalid",
            "reason": "negative_weight",
            "fallback_applied": True,
        }
    }))

    vm = read_validation_panel_view_model(source)

    assert vm.source_mode == "governance_summary"
    policy_warning = next(finding for finding in vm.warning_findings if finding.code == "negative_weight")
    assert policy_warning.title == "Policy validation"
    assert "Safe defaults were applied" in policy_warning.message
    assert policy_warning.suggested_action == "Review policy configuration"


def test_validation_panel_surfaces_policy_validation_warning_from_execution_record_recovery_metrics() -> None:
    base = _execution_record()
    record = replace(base, observability=replace(base.observability, metrics={
        "recovery": {
            "policy_validation": {
                "status": "invalid",
                "reason": "zero_total_weight",
                "fallback_applied": True,
            }
        }
    }))

    vm = read_validation_panel_view_model(_working_save(), execution_record=record)

    assert vm.source_mode == "execution_guard"
    policy_warning = next(finding for finding in vm.warning_findings if finding.code == "zero_total_weight")
    assert policy_warning.title == "Policy validation"
    assert "Safe defaults were applied" in policy_warning.message
