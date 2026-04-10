from __future__ import annotations

from src.contracts.nex_contract import ValidationReport
from src.designer.models.designer_approval_flow import DesignerApprovalFlowState
from src.storage.models.commit_snapshot_model import CommitApprovalModel, CommitLineageModel, CommitSnapshotMeta, CommitSnapshotModel, CommitValidationModel
from src.storage.models.execution_record_model import ExecutionArtifactsModel, ExecutionDiagnosticsModel, ExecutionInputModel, ExecutionMetaModel, ExecutionObservabilityModel, ExecutionOutputModel, ExecutionRecordModel, ExecutionSourceModel, ExecutionTimelineModel, NodeResultsModel
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.action_schema import read_builder_action_schema
from src.ui.designer_panel import read_designer_panel_view_model
from src.ui.execution_panel import read_execution_panel_view_model
from src.ui.i18n import normalize_ui_language, ui_text
from src.ui.storage_panel import read_storage_view_model
from src.ui.validation_panel import read_validation_panel_view_model


def _working_save(app_language: str = "ko") -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "n1"}], edges=[], entry="n1", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata={"app_language": app_language}),
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


def test_ui_i18n_normalizes_locale_and_falls_back_to_english() -> None:
    assert normalize_ui_language("ko-KR") == "ko"
    assert normalize_ui_language("fr") == "en"
    assert ui_text("designer.action.submit_request", app_language="fr") == "Submit request"


def test_ui_i18n_localizes_designer_panel_strings_from_working_save_preference() -> None:
    vm = read_designer_panel_view_model(
        _working_save("ko"),
        approval_flow=DesignerApprovalFlowState(
            approval_id="approval-1",
            intent_ref="intent-1",
            patch_ref="patch-1",
            precheck_ref="pre-1",
            preview_ref="preview-1",
            current_stage="awaiting_decision",
            final_outcome="approved_for_commit",
        ),
    )
    assert vm.request_state.input_placeholder == "원하는 회로 변경 내용을 입력하세요."
    assert vm.suggested_actions[0].label == "요청 제출"


def test_ui_i18n_localizes_storage_execution_validation_and_builder_actions() -> None:
    working_save = _working_save("ko")
    storage_vm = read_storage_view_model(working_save, latest_commit_snapshot=_commit(), latest_execution_record=_run())
    validation_vm = read_validation_panel_view_model(working_save, validation_report=ValidationReport(role="working_save", findings=[], blocking_count=0, warning_count=0, result="passed"))
    execution_vm = read_execution_panel_view_model(working_save)
    action_vm = read_builder_action_schema(
        working_save,
        storage_view=storage_vm,
        validation_view=validation_vm,
        execution_view=execution_vm,
    )

    assert storage_vm.lifecycle_summary.summary_label == "현재 드래프트를 편집 중입니다"
    assert storage_vm.available_actions[0].label == "드래프트 저장"
    assert execution_vm.control_state.available_actions[0].label == "실행"
    assert validation_vm.suggested_actions[0].label == "최상위 이슈로 이동"
    actions = {a.action_id: a for a in action_vm.primary_actions + action_vm.secondary_actions + action_vm.contextual_actions}
    assert actions["save_working_save"].label == "드래프트 저장"


def test_ui_i18n_exposes_beginner_placeholder_and_terms() -> None:
    assert ui_text("designer.request.input_placeholder.beginner", app_language="en") == "What would you like to build? Describe your goal."
    assert ui_text("designer.request.input_placeholder.beginner", app_language="ko") == "어떤 것을 만들고 싶으세요? 목표를 설명해주세요."
    assert ui_text("beginner.term.circuit", app_language="en") == "workflow"
    assert ui_text("beginner.term.circuit", app_language="ko") == "워크플로우"
