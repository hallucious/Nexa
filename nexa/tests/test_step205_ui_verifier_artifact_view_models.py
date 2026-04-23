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
    NodeResultsModel,
)
from src.ui.artifact_viewer import read_artifact_viewer_view_model
from src.ui.validation_panel import read_validation_panel_view_model


VERIFIER_PAYLOAD = {
    "target_ref": "node.draft.output",
    "aggregate_status": "warning",
    "aggregate_score": 0.5,
    "aggregate_confidence": 0.5,
    "blocking_reason_codes": ["REQUIREMENT_TEXT_TOO_SHORT"],
    "recommended_next_step": "continue_with_warnings",
    "constituent_results": [
        {
            "verifier_id": "answer_quality",
            "verifier_type": "requirement",
            "target_ref": "node.draft.output",
            "status": "warning",
            "reason_code": "REQUIREMENT_TEXT_TOO_SHORT",
            "explanation": "requirement verification completed",
            "findings": [
                {
                    "finding_id": "answer_quality::length",
                    "severity": "warning",
                    "category": "requirement",
                    "reason_code": "REQUIREMENT_TEXT_TOO_SHORT",
                    "message": "output text length is below minimum 10",
                    "suggested_action": "expand the response",
                }
            ],
        }
    ],
}


def _record() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-verifier-ui",
            record_format_version="1.0.0",
            created_at="2026-04-07T00:00:00Z",
            started_at="2026-04-07T00:00:00Z",
            finished_at="2026-04-07T00:00:02Z",
            status="completed",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(),
        artifacts=ExecutionArtifactsModel(
            artifact_refs=[
                ArtifactRecordCard(
                    artifact_id="artifact::validation_report::001",
                    artifact_type="validation_report",
                    producer_node="draft",
                    producer_ref="node.draft",
                    ref="artifact://run-verifier-ui/artifact::validation_report::001",
                    summary="verification report (warning)",
                    artifact_schema_version="1.0.0",
                    validation_status="partial",
                    trace_refs=["trace://run-verifier-ui/draft/verifier"],
                    metadata={"aggregate_status": "warning", "report_kind": "verifier"},
                    payload_preview=VERIFIER_PAYLOAD,
                )
            ],
            artifact_count=1,
            artifact_summary="1 artifact ref(s) recorded",
        ),
        diagnostics=ExecutionDiagnosticsModel(),
        observability=ExecutionObservabilityModel(
            verifier_summary={"verifier_report_count": 1, "status_counts": {"warning": 1}}
        ),
    )


def test_step205_artifact_viewer_projects_verifier_artifact_detail() -> None:
    vm = read_artifact_viewer_view_model(_record(), selected_artifact_id="artifact::validation_report::001")

    assert vm.artifact_list[0].category == "verification"
    assert vm.selected_artifact is not None
    assert vm.selected_artifact.body_mode == "structured"
    assert vm.selected_artifact.structured_preview["aggregate_status"] == "warning"
    assert vm.selected_artifact.metadata.artifact_schema_version == "1.0.0"
    assert vm.selected_artifact.metadata.validation_status == "partial"
    assert vm.selected_artifact.integrity.verifier_status == "warning"
    assert vm.selected_artifact.lineage.producer_ref == "node.draft"


def test_step205_validation_panel_projects_verifier_findings_from_execution_record() -> None:
    vm = read_validation_panel_view_model(None, execution_record=_record())

    assert vm.source_mode == "execution_guard"
    assert vm.overall_status == "pass_with_warnings"
    assert vm.summary.warning_count >= 1
    assert any(f.code == "REQUIREMENT_TEXT_TOO_SHORT" for f in vm.warning_findings)
