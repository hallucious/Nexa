from __future__ import annotations

from src.contracts.nex_contract import ValidationFinding, ValidationReport
from src.engine.execution_event import ExecutionEvent
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
    NodeResultCard,
    NodeResultsModel,
    OutputResultCard,
)
from src.storage.models.shared_sections import CircuitModel, ResourcesModel, StateModel
from src.storage.models.working_save_model import RuntimeModel, UIModel, WorkingSaveMeta, WorkingSaveModel
from src.ui.builder_shell import read_builder_shell_view_model
from src.ui.execution_panel import read_execution_panel_view_model


def _working_save(*, mobile: bool = False, provider_session: bool = False, external_input: str | None = None) -> WorkingSaveModel:
    metadata = {"app_language": "en-US"}
    if mobile:
        metadata["viewport_tier"] = "mobile"
    if provider_session:
        metadata["provider_session_keys"] = {"gpt": "sk-test-session"}
    nodes = []
    plugins: dict[str, object] = {}
    if external_input == "url":
        nodes = [{"id": "reader", "execution": {"plugin": {"plugin_id": "nexa.url_reader"}}}]
        plugins = {"nexa.url_reader": {}}
    elif external_input == "file":
        nodes = [{"id": "reader", "execution": {"plugin": {"plugin_id": "nexa.file_reader"}}}]
        plugins = {"nexa.file_reader": {}}
    return WorkingSaveModel(
        meta=WorkingSaveMeta(format_version="1.0.0", storage_role="working_save", working_save_id="ws-001", name="Draft"),
        circuit=CircuitModel(nodes=nodes, edges=[], entry=(nodes[0]["id"] if nodes else None), outputs=[]),
        resources=ResourcesModel(prompts={}, providers={}, plugins=plugins),
        state=StateModel(input={}, working={}, memory={}),
        runtime=RuntimeModel(status="draft", validation_summary={}, last_run={}, errors=[]),
        ui=UIModel(layout={}, metadata=metadata),
    )


def _validation_report_blocked() -> ValidationReport:
    return ValidationReport(
        role="working_save",
        findings=[ValidationFinding(code="MISSING_INPUT", category="structural", severity="high", blocking=True, location="node:reader", message="Connect a model before running")],
        blocking_count=1,
        warning_count=0,
        result="failed",
    )


def _running_record() -> ExecutionRecordModel:
    return ExecutionRecordModel(
        meta=ExecutionMetaModel(run_id="run-001", record_format_version="1.0.0", created_at="2026-04-13T00:00:00Z", started_at="2026-04-13T00:00:00Z", status="running"),
        source=ExecutionSourceModel(commit_id="commit-001", trigger_type="manual_run"),
        input=ExecutionInputModel(),
        timeline=ExecutionTimelineModel(total_duration_ms=3200, event_count=3, node_order=["n1", "n2"]),
        node_results=NodeResultsModel(results=[
            NodeResultCard(node_id="n1", status="success", route_summary={"estimated_cost": 0.2}),
            NodeResultCard(node_id="n2", status="partial", route_summary={"estimated_cost": 0.9}),
        ]),
        outputs=ExecutionOutputModel(final_outputs=[OutputResultCard(output_ref="result", source_node="n2", value_summary="partial result", value_payload="partial result")]),
        artifacts=ExecutionArtifactsModel(),
        diagnostics=ExecutionDiagnosticsModel(),
        observability=ExecutionObservabilityModel(
            metrics={"cost_estimate": 1.25, "actual_cost": 0.75},
            trace_intelligence_summary={"highest_cost_nodes": ["n2", "n1"]},
        ),
    )


def test_execution_panel_surfaces_phase6_cost_visibility() -> None:
    vm = read_execution_panel_view_model(_working_save(), execution_record=_running_record())

    assert vm.cost_visibility.visible is True
    assert vm.cost_visibility.estimated_cost == 1.25
    assert vm.cost_visibility.actual_cost == 0.75
    assert vm.cost_visibility.top_cost_node_id == "n2"
    assert "Estimated cost" in (vm.cost_visibility.summary or "")


def test_execution_panel_surfaces_phase6_waiting_feedback_for_streaming_run() -> None:
    live_events = [
        ExecutionEvent(
            type="token_chunk",
            execution_id="exec-001",
            node_id="n2",
            timestamp_ms=1,
            payload={"text": "Hello"},
        )
    ]
    vm = read_execution_panel_view_model(_working_save(), execution_record=_running_record(), live_events=live_events)

    assert vm.waiting_feedback.visible is True
    assert vm.waiting_feedback.state == "streaming"
    assert vm.waiting_feedback.next_action_target == "execution"


def test_builder_shell_surfaces_phase6_mobile_first_run_path() -> None:
    vm = read_builder_shell_view_model(_working_save(mobile=True))

    assert vm.mobile_first_run.visible is True
    assert vm.mobile_first_run.compact_mode is True
    assert len(vm.mobile_first_run.steps) == 5
    assert vm.mobile_first_run.primary_action_target == "designer"
    assert vm.contextual_help.stage == "start"


def test_builder_shell_surfaces_phase6_contextual_help_for_blocked_state() -> None:
    vm = read_builder_shell_view_model(_working_save(external_input="file"), validation_report=_validation_report_blocked())

    assert vm.contextual_help.visible is True
    assert vm.contextual_help.stage == "fix"
    assert vm.contextual_help.suggested_actions[0].target == "validation"


def test_builder_shell_surfaces_phase6_privacy_transparency_for_session_key_and_external_input() -> None:
    vm = read_builder_shell_view_model(_working_save(provider_session=True, external_input="url"))

    assert vm.privacy_transparency.visible is True
    assert vm.privacy_transparency.requires_acknowledgement is True
    fact_values = {fact.fact_id: fact.value for fact in vm.privacy_transparency.facts}
    assert fact_values["provider_access"] == "Session-only key"
    assert fact_values["external_input"] == "Reads from a URL"
