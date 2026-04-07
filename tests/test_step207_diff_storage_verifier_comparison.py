from __future__ import annotations

from src.storage.models.execution_record_model import (
    ArtifactRecordCard,
    ExecutionArtifactsModel,
    ExecutionDiagnosticsModel,
    ExecutionInputModel,
    ExecutionMetaModel,
    ExecutionObservabilityModel,
    ExecutionOutputModel,
    ExecutionRecordModel,
    ExecutionSourceModel,
    ExecutionTimelineModel,
    NodeResultCard,
    NodeResultsModel,
)
from src.ui.diff_viewer import read_diff_view_model
from src.ui.storage_panel import read_storage_view_model


def _run(run_id: str, *, verifier_status: str, reason_codes: list[str], status_counts: dict[str, int]) -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id=run_id,
            record_format_version="1.0.0",
            created_at="2026-04-07T00:00:00Z",
            started_at="2026-04-07T00:00:00Z",
            finished_at="2026-04-07T00:00:02Z",
            status="completed" if verifier_status != "fail" else "failed",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(trace_ref=f"trace://{run_id}", event_stream_ref=f"events://{run_id}"),
        node_results=NodeResultsModel(
            results=[
                NodeResultCard(
                    node_id="draft",
                    status="success" if verifier_status != "fail" else "failed",
                    output_summary="answer",
                    typed_artifact_refs=[f"artifact::{run_id}::typed"],
                    verifier_status=verifier_status,
                    verifier_reason_codes=reason_codes,
                    artifact_refs=[f"artifact::{run_id}::report"],
                )
            ]
        ),
        outputs=ExecutionOutputModel(output_summary="1 output"),
        artifacts=ExecutionArtifactsModel(
            artifact_refs=[
                ArtifactRecordCard(
                    artifact_id=f"artifact::{run_id}::report",
                    artifact_type="validation_report",
                    validation_status=verifier_status,
                    artifact_schema_version="1.0.0",
                    recorded_at="2026-04-07T00:00:01Z",
                    trace_refs=[f"trace://{run_id}/draft/verifier"],
                ),
                ArtifactRecordCard(
                    artifact_id=f"artifact::{run_id}::typed",
                    artifact_type="json_object",
                    validation_status=verifier_status,
                    artifact_schema_version="1.0.0",
                    recorded_at="2026-04-07T00:00:01Z",
                ),
            ],
            artifact_count=2,
        ),
        diagnostics=ExecutionDiagnosticsModel(warnings=[], errors=[]),
        observability=ExecutionObservabilityModel(
            verifier_summary={"verifier_report_count": 1, "status_counts": status_counts, "blocking_reason_codes": reason_codes}
        ),
    )


def test_step207_diff_viewer_projects_verifier_changes_for_run_comparison() -> None:
    source = _run("run-001", verifier_status="warning", reason_codes=["REQUIREMENT_TEXT_TOO_SHORT"], status_counts={"warning": 1})
    target = _run("run-002", verifier_status="pass", reason_codes=[], status_counts={"pass": 1})

    vm = read_diff_view_model(diff_mode="run_vs_run", source=source, target=target)

    assert vm.viewer_status == "ready"
    assert vm.summary.verification_change_count >= 1
    assert any(group.group_label == "Verification" for group in vm.grouped_changes)
    verification_group = next(group for group in vm.grouped_changes if group.group_label == "Verification")
    assert any("Verifier outcome" in item.short_label or "Verifier summary" in item.short_label for item in verification_group.changes)


def test_step207_storage_panel_surfaces_verifier_summary_and_compare_runs_availability() -> None:
    run = _run("run-002", verifier_status="warning", reason_codes=["REQUIREMENT_TEXT_TOO_SHORT"], status_counts={"warning": 1})

    vm = read_storage_view_model(
        run,
        latest_execution_record=run,
        recent_run_refs=["execution_record:run-002", "execution_record:run-001"],
    )

    assert vm.execution_record_card is not None
    assert vm.execution_record_card.verification_available is True
    assert vm.execution_record_card.verifier_summary_label is not None
    assert "reports=1" in vm.execution_record_card.verifier_summary_label
    assert vm.execution_record_card.can_compare_runs is True
    assert any(action.action_type == "compare_runs" and action.enabled for action in vm.available_actions)
