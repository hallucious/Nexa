from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.action_schema import read_builder_action_schema
from src.ui.beginner_surface_gate import BEGINNER_LOCKED_DEEP_SURFACE_REASON
from src.ui.execution_panel import read_execution_panel_view_model
from src.ui.storage_panel import read_storage_view_model
from src.ui.validation_panel import read_validation_panel_view_model
from src.ui.designer_panel import read_designer_panel_view_model


def _empty_working_save() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-empty", name="Empty Draft"),
        circuit=CircuitModel(nodes=[], edges=[], entry=None, outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={}),
    )


def _working_save(*, metadata: dict | None = None, last_run: dict | None = None) -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run=dict(last_run or {}), errors=[]),
        ui=UIModel(layout={}, metadata=dict(metadata or {})),
    )


def _commit() -> CommitSnapshotModel:
    return CommitSnapshotModel(
        meta=CommitSnapshotMeta(format_version="1.0.0", storage_role="commit_snapshot", commit_id="commit-001", source_working_save_id="ws-001"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        validation=CommitValidationModel(validation_result="passed", summary={}),
        approval=CommitApprovalModel(approval_completed=True, approval_status="approved", summary={}),
        lineage=CommitLineageModel(source_working_save_id="ws-001", metadata={}),
    )


def _run(status: str = "completed") -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-06T00:00:00Z", started_at="2026-04-06T00:00:00Z", finished_at="2026-04-06T00:00:05Z", status=status),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(),
    )


def _validation(result: str = "passed") -> ValidationReport:
    findings = []
    blocking = 0
    if result == "failed":
        findings = [ValidationFinding(code="BLOCKED", category="structural", severity="high", blocking=True, location="node:n1", message="blocked")]
        blocking = 1
    return ValidationReport(role="working_save", findings=findings, blocking_count=blocking, warning_count=0, result=result)


def test_action_schema_enables_commit_when_review_and_approval_are_ready() -> None:
    storage = read_storage_view_model(_working_save(), latest_commit_snapshot=_commit(), latest_execution_record=_run())
    validation = read_validation_panel_view_model(_working_save(), validation_report=_validation("passed"))
    execution = read_execution_panel_view_model(_working_save(), execution_record=_run())
    designer = read_designer_panel_view_model(_working_save(), approval_flow=DesignerApprovalFlowState(approval_id="approval-1", intent_ref="intent-1", patch_ref="patch-1", precheck_ref="pre-1", preview_ref="preview-1", current_stage="awaiting_decision", final_outcome="approved_for_commit"))

    vm = read_builder_action_schema(_working_save(), storage_view=storage, validation_view=validation, execution_view=execution, designer_view=designer)
    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["commit_snapshot"].enabled is True
    assert actions["run_current"].enabled is True
    assert actions["approve_for_commit"].enabled is True


def test_action_schema_disables_run_and_commit_when_validation_is_blocked() -> None:
    storage = read_storage_view_model(_working_save())
    validation = read_validation_panel_view_model(_working_save(), validation_report=_validation("failed"))
    execution = read_execution_panel_view_model(_working_save(), execution_record=_run())

    vm = read_builder_action_schema(_working_save(), storage_view=storage, validation_view=validation, execution_view=execution)
    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["commit_snapshot"].enabled is False
    assert actions["run_current"].enabled is False


def test_action_schema_enables_cancel_only_for_running_execution() -> None:
    execution = read_execution_panel_view_model(_working_save(), execution_record=_run(status="running"))
    vm = read_builder_action_schema(_working_save(), execution_view=execution)
    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["cancel_run"].enabled is True


def test_action_schema_prioritizes_commit_snapshot_runtime_actions_for_approved_snapshot() -> None:
    storage = read_storage_view_model(_commit())
    validation = read_validation_panel_view_model(_commit())
    vm = read_builder_action_schema(_commit(), storage_view=storage, validation_view=validation)

    primary_ids = [a.action_id for a in vm.primary_actions]
    assert "run_from_commit" in primary_ids
    assert "open_latest_commit" in primary_ids
    assert "save_working_save" not in primary_ids
    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["run_from_commit"].enabled is True


def test_action_schema_prioritizes_execution_record_inspection_actions_for_history_role() -> None:
    storage = read_storage_view_model(_run())
    execution = read_execution_panel_view_model(_run(), execution_record=_run())
    vm = read_builder_action_schema(_run(), storage_view=storage, execution_view=execution)

    primary_ids = [a.action_id for a in vm.primary_actions]
    assert "open_latest_run" in primary_ids
    assert "replay_latest" not in primary_ids
    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["open_latest_run"].enabled is True


def test_action_schema_surfaces_provider_setup_and_template_actions_for_empty_beginner_workspace(monkeypatch, tmp_path) -> None:
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PERPLEXITY_API_KEY", "PPLX_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)

    designer = read_designer_panel_view_model(_empty_working_save())
    vm = read_builder_action_schema(_empty_working_save(), designer_view=designer)

    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["open_provider_setup"].enabled is True
    assert actions["create_circuit_from_template"].enabled is True


def test_action_schema_surfaces_external_input_actions_for_empty_beginner_workspace(monkeypatch, tmp_path) -> None:
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "PERPLEXITY_API_KEY", "PPLX_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)

    designer = read_designer_panel_view_model(_empty_working_save())
    vm = read_builder_action_schema(_empty_working_save(), designer_view=designer)

    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["open_file_input"].enabled is True
    assert actions["enter_url_input"].enabled is True


def test_action_schema_surfaces_return_use_actions_after_first_success() -> None:
    working = _working_save(metadata={"beginner_first_success_achieved": True})
    storage = read_storage_view_model(working, latest_execution_record=_run())
    execution = read_execution_panel_view_model(working, execution_record=_run())

    vm = read_builder_action_schema(working, storage_view=storage, execution_view=execution)
    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["open_circuit_library"].enabled is True
    assert actions["open_result_history"].enabled is True
    assert actions["open_feedback_channel"].enabled is True


def test_action_schema_surfaces_return_use_actions_for_execution_record_history_role() -> None:
    storage = read_storage_view_model(_run())
    execution = read_execution_panel_view_model(_run(), execution_record=_run())

    vm = read_builder_action_schema(_run(), storage_view=storage, execution_view=execution)
    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["open_result_history"].enabled is True
    assert actions["open_feedback_channel"].enabled is True


def test_action_schema_surfaces_cost_review_action_when_expected_usage_is_available() -> None:
    working = _working_save(last_run={"estimated_cost": 1.25})
    execution = read_execution_panel_view_model(working)

    vm = read_builder_action_schema(working, execution_view=execution)
    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["review_run_cost"].enabled is True


def test_action_schema_surfaces_watch_progress_action_for_running_execution() -> None:
    execution = read_execution_panel_view_model(_working_save(), execution_record=_run(status="running"))

    vm = read_builder_action_schema(_working_save(), execution_view=execution)
    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["watch_run_progress"].enabled is True




def test_action_schema_disables_deep_actions_before_first_success_even_with_completed_execution() -> None:
    working = _working_save()
    storage = read_storage_view_model(working, latest_execution_record=_run())
    execution = read_execution_panel_view_model(working, execution_record=_run(status="completed"))

    vm = read_builder_action_schema(working, storage_view=storage, execution_view=execution)
    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}

    assert "open_visual_editor" not in actions
    assert "open_node_configuration" not in actions
    assert "open_runtime_monitoring" not in actions
    assert actions["replay_latest"].enabled is False
    assert actions["open_diff"].enabled is False
    assert actions["replay_latest"].reason_disabled == BEGINNER_LOCKED_DEEP_SURFACE_REASON
    assert actions["open_diff"].reason_disabled == BEGINNER_LOCKED_DEEP_SURFACE_REASON


def test_action_schema_surfaces_core_workspace_navigation_actions_after_beginner_unlock() -> None:
    working = _working_save(metadata={"beginner_first_success_achieved": True})
    execution = read_execution_panel_view_model(working, execution_record=_run())

    vm = read_builder_action_schema(working, execution_view=execution)
    actions = {a.action_id: a for a in vm.primary_actions + vm.secondary_actions + vm.contextual_actions}
    assert actions["open_visual_editor"].enabled is True
    assert actions["open_node_configuration"].enabled is True
    assert actions["open_runtime_monitoring"].enabled is True
