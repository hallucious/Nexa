from __future__ import annotations

from src.automation.output_destination import attempt_delivery
from src.contracts.status_taxonomy import is_canonical_reason_code, lookup_reason_code_record
from src.governance.quota import QuotaPolicy, QuotaScope, QuotaStateRecord, evaluate_quota
from src.safety.input_safety import evaluate_input_safety
from src.storage.models.execution_record_model import (
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
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.execution_panel import read_execution_panel_view_model
from src.ui.validation_panel import read_validation_panel_view_model


def test_phase1_batchC_input_safety_reason_codes_are_canonical() -> None:
    evaluation = evaluate_input_safety([
        {"input_ref": "user.prompt", "content": "api_key=sk-ABCDEF1234567890 and user@example.com"}
    ])
    reason_codes = [finding["reason_code"] for finding in evaluation["findings"]]
    assert "safety.credential.exposed_secret_pattern" in reason_codes
    assert "safety.personal.detected_personal_data_warning" in reason_codes
    assert all(is_canonical_reason_code(code) for code in reason_codes)
    secret_record = lookup_reason_code_record("safety.credential.exposed_secret_pattern")
    assert secret_record is not None
    assert secret_record.subsystem == "safety"
    assert secret_record.severity == "blocking"


def test_phase1_batchC_quota_and_delivery_reason_codes_are_canonical() -> None:
    decision = evaluate_quota(
        scope=QuotaScope(scope_type="workspace", scope_ref="workspace.demo"),
        policy=QuotaPolicy(policy_id="quota.demo", scope_ref="workspace.demo", max_run_count=0, hard_block_enabled=True),
        state_record=QuotaStateRecord(scope_ref="workspace.demo", period_ref="day:default", consumed_run_count=0),
        requested_action_type="run_launch",
        estimated_usage={"run_count": 1},
    )
    assert decision.blocking_reason_code == "quota.run.count_limit_exceeded"
    assert is_canonical_reason_code(decision.blocking_reason_code)

    delivery = attempt_delivery(
        capability={
            "destination_type": "slack",
            "destination_ref": "slack.primary",
            "supports_text": True,
            "supports_structured_payload": False,
            "supports_attachments": False,
            "supports_idempotency_key": False,
            "supports_retry": False,
            "auth_mode": "managed",
        },
        plan={
            "destination_type": "slack",
            "destination_ref": "slack.primary",
            "selected_output_ref": "node_a",
            "payload_projection_mode": "final_output",
        },
        outputs={"node_a": {"message": "structured"}},
    )
    assert delivery["attempt"]["failure_reason_code"] == "delivery.payload.structured_payload_unsupported"
    assert is_canonical_reason_code(delivery["attempt"]["failure_reason_code"])


def _working_save_with_governance() -> WorkingSaveModel:
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=[{"id": "draft"}], edges=[], entry="draft", outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins={}),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(
            status="execution_failed",
            validation_summary={},
            last_run={
                "run_id": "run-001",
                "status": "failed",
                "governance": {
                    "launch_status": "quota_blocked",
                    "quota_status": "blocked",
                    "quota_reason_code": "quota.run.count_limit_exceeded",
                    "reason_codes": ["quota.run.count_limit_exceeded"],
                    "top_reason_code": "quota.run.count_limit_exceeded",
                },
            },
            errors=[],
        ),
        ui=UIModel(layout={}, metadata={}),
    )


def test_phase1_batchC_validation_panel_projects_governance_summary_from_working_save_last_run() -> None:
    vm = read_validation_panel_view_model(_working_save_with_governance())
    assert vm.source_mode == "governance_summary"
    assert vm.overall_status == "blocked"
    assert vm.blocking_findings[0].code == "quota.run.count_limit_exceeded"
    assert vm.blocking_findings[0].category == "governance"


def _record_with_governance() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(
            run_id="run-001",
            record_format_version="1.0.0",
            created_at="2026-04-10T00:00:00Z",
            started_at="2026-04-10T00:00:00Z",
            finished_at="2026-04-10T00:00:05Z",
            status="completed",
        ),
        source=ExecutionSourceModel(commit_id="commit-001", working_save_id="ws-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(total_duration_ms=5000, event_count=2),
        node_results=NodeResultsModel(),
        outputs=ExecutionOutputModel(output_summary="done"),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(),
        observability=ExecutionObservabilityModel(
            metrics={
                "governance": {
                    "launch_status": "allowed",
                    "safety_status": "warning",
                    "safety_reason_code": "safety.personal.detected_personal_data_warning",
                    "delivery_status": "blocked",
                    "delivery_reason_code": "delivery.destination.authorization_blocked",
                    "delivery_destination_ref": "email.primary",
                    "reason_codes": [
                        "safety.personal.detected_personal_data_warning",
                        "delivery.destination.authorization_blocked",
                    ],
                    "top_reason_code": "safety.personal.detected_personal_data_warning",
                }
            }
        ),
    )


def test_phase1_batchC_execution_panel_projects_governance_and_delivery_summary() -> None:
    vm = read_execution_panel_view_model(_record_with_governance())
    assert any(signal.family == "safety_status" and signal.reason_code == "safety.personal.detected_personal_data_warning" for signal in vm.governance_signals)
    assert vm.delivery_outcome is not None
    assert vm.delivery_outcome.status == "blocked"
    assert vm.delivery_outcome.reason_code == "delivery.destination.authorization_blocked"
    assert vm.delivery_outcome.destination_ref == "email.primary"
