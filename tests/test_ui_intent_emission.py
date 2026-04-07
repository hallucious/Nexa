from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_interaction_hub import read_builder_interaction_hub_view_model
from src.ui.intent_emission import read_intent_emission_view_model


def _working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[{"name": "out", "source": "n1"}]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _run() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at="2026-04-06T00:00:05Z", status="completed"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def _validation_report(blocking: bool = False) -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="MISSING_INPUT", category="structural", severity="high", blocking=True, location="node:n1", message="missing input")] if blocking else [],
        blocking_count=1 if blocking else 0,
        warning_count=0,
        result="failed" if blocking else "passed",
    )


def _approval(commit_eligible: bool) -> DesignerApprovalFlowState:
    return DesignerApprovalFlowState(
        approval_id="approval-001",
        intent_ref="intent-001",
        patch_ref="patch-001",
        precheck_ref="pre-001",
        preview_ref="preview-001",
        current_stage="awaiting_decision",
        final_outcome="approved_for_commit" if commit_eligible else "pending",
        precheck_status="pass",
    )


def test_intent_emission_projects_enabled_builder_actions_into_emit_ready_contracts() -> None:
    hub = read_builder_interaction_hub_view_model(_working_save(), validation_report=_validation_report(), execution_record=_run(), approval_flow=_approval(False))
    vm = read_intent_emission_view_model(_working_save(), interaction_hub=hub)

    assert vm.emission_status in {"ready", "attention"}
    assert vm.enabled_emission_count >= 1
    assert any(item.action_id == "run_current" for item in vm.emissions)


def test_intent_emission_blocks_commit_related_emissions_when_review_state_is_blocked() -> None:
    hub = read_builder_interaction_hub_view_model(_working_save(), validation_report=_validation_report(True), execution_record=_run(), approval_flow=_approval(False))
    vm = read_intent_emission_view_model(_working_save(), interaction_hub=hub)
    commit = next(item for item in vm.emissions if item.action_id == "commit_snapshot")

    assert commit.emit_allowed is False
    assert commit.reason_blocked is not None
