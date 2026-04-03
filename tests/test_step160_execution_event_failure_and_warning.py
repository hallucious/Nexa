from __future__ import annotations

from src.circuit.circuit_runner import CircuitRunner
from src.engine.execution_event_emitter import ExecutionEventEmitter
from src.engine.execution_event import ExecutionEvent
from src.engine.execution_timeline import ExecutionTimelineBuilder
from src.engine.node_execution_runtime import NodeExecutionRuntime, ReviewRequiredPause
from src.engine.validation.result import Severity, ValidationResult, ValidationDecision, Violation


class DummyProviderExecutor:
    def execute(self, request):
        raise RuntimeError("not used in this test")


class DummyRegistry:
    def __init__(self):
        self._configs = {
            "cfg.ok": {"config_id": "cfg.ok"},
            "cfg.fail": {"config_id": "cfg.fail"},
        }

    def get(self, config_id):
        return self._configs[config_id]


class SuccessRuntime:
    def __init__(self):
        self.event_emitter = ExecutionEventEmitter(event_file=None)
        self.execution_id = "runtime-default"

    def set_execution_id(self, execution_id):
        self.execution_id = execution_id

    def _emit_event(self, event_type, payload, node_id=None):
        self.event_emitter.emit(
            ExecutionEvent.now(
                event_type,
                payload,
                execution_id=self.execution_id,
                node_id=node_id,
            )
        )

    def execute_by_config_id(self, registry, config_id, state):
        class Result:
            def __init__(self, output):
                self.output = output

        return Result(output=f"done:{config_id}")


class FailingRuntime(SuccessRuntime):
    def execute_by_config_id(self, registry, config_id, state):
        raise RuntimeError(f"boom:{config_id}")


class ReviewPauseRuntime(SuccessRuntime):
    def execute_by_config_id(self, registry, config_id, state):
        raise ReviewRequiredPause(
            node_id="node_a",
            payload={
                "reason": "sample_validation",
                "is_blocking": True,
            },
        )


class WarningCircuitRunner(CircuitRunner):
    def _run_determinism_validation(self, circuit, *, strict_determinism):
        return ValidationResult(
            success=False,
            engine_revision="test",
            structural_fingerprint="fp",
            violations=[
                Violation(
                    rule_id="DET-ADVISORY",
                    rule_name="determinism advisory",
                    severity=Severity.WARNING,
                    location_type="circuit",
                    location_id=None,
                    message="advisory violation",
                )
            ],
        )


def test_runtime_emits_failed_node_completed_event_on_validation_error(tmp_path):
    runtime = NodeExecutionRuntime(
        provider_executor=DummyProviderExecutor(),
        plugin_registry={},
        event_emitter=ExecutionEventEmitter(event_file=None),
        observability_file=str(tmp_path / "obs.jsonl"),
    )
    runtime.set_execution_id("exec-node-fail")

    config = {
        "config_id": "cfg.validation.fail",
        "prompt": {
            "prompt_id": "main",
            "inputs": {"question": "input.question"},
        },
        "validation_rules": ["require_answer"],
        "runtime_config": {"write_observability": False},
    }

    try:
        runtime.execute(config, {"question": "What is Nexa?"})
    except ValueError as exc:
        assert "answer missing" in str(exc)
    else:
        raise AssertionError("expected validation failure")

    events = runtime.get_execution_events()
    assert [event.type for event in events] == ["node_started", "node_completed"]
    completed = events[-1]
    assert completed.node_id == "cfg.validation.fail"
    assert completed.payload["status"] == "failed"
    assert completed.payload["error_type"] == "ValueError"


def test_circuit_runner_emits_execution_failed_event_on_runtime_error():
    runtime = FailingRuntime()
    registry = DummyRegistry()
    runner = CircuitRunner(runtime, registry)

    circuit = {
        "id": "sample-circuit",
        "nodes": [
            {"id": "node_a", "execution_config_ref": "cfg.fail", "depends_on": []},
        ],
    }

    try:
        runner.execute(circuit, {"input_value": "x"})
    except RuntimeError as exc:
        assert "boom:cfg.fail" in str(exc)
    else:
        raise AssertionError("expected runtime failure")

    events = runtime.event_emitter.get_events()
    assert [event.type for event in events] == ["execution_started", "execution_failed"]
    failed = events[-1]
    assert failed.payload["circuit_id"] == "sample-circuit"
    assert failed.payload["executed_nodes"] == 0
    assert failed.payload["error_type"] == "RuntimeError"


def test_circuit_runner_emits_warning_event_for_advisory_post_validation():
    runtime = SuccessRuntime()
    registry = DummyRegistry()
    runner = WarningCircuitRunner(runtime, registry)

    circuit = {
        "id": "sample-circuit",
        "nodes": [
            {"id": "node_a", "execution_config_ref": "cfg.ok", "depends_on": []},
        ],
    }

    result = runner.execute(circuit, {"input_value": "x"})
    assert result["node_a"] == "done:cfg.ok"

    events = runtime.event_emitter.get_events()
    assert [event.type for event in events] == [
        "execution_started",
        "execution_completed",
        "warning",
    ]
    warning = events[-1]
    assert warning.payload["reason"] == "advisory determinism violations detected"
    assert warning.payload["warning_count"] == 1


def test_timeline_builder_accepts_execution_failed_as_terminal_event():
    events = [
        ExecutionEvent("execution_started", "run1", None, 0, {}),
        ExecutionEvent("node_started", "run1", "A", 10, {}),
        ExecutionEvent("node_completed", "run1", "A", 20, {"status": "failed", "error": "boom"}),
        ExecutionEvent("execution_failed", "run1", None, 25, {"error": "boom"}),
    ]

    bundle = ExecutionTimelineBuilder().build(events)
    assert bundle.timeline.duration_ms == 25
    assert bundle.profile.total_nodes == 1
    assert bundle.profile.failed_nodes == 1
    assert bundle.profile.succeeded_nodes == 0
    assert bundle.timeline.node_spans[0].status == "failed"
    assert bundle.timeline.node_spans[0].error == "boom"


def test_circuit_runner_emits_execution_paused_event_on_review_gate_signal():
    runtime = ReviewPauseRuntime()
    registry = DummyRegistry()
    runner = CircuitRunner(runtime, registry)

    circuit = {
        "id": "sample-circuit",
        "nodes": [
            {"id": "node_a", "execution_config_ref": "cfg.ok", "depends_on": []},
        ],
    }

    result = runner.execute(circuit, {"input_value": "x"})
    assert result.governance.final_status == "paused"
    assert result.governance.execution_completed is False

    events = runtime.event_emitter.get_events()
    assert [event.type for event in events] == ["execution_started", "execution_paused"]
    paused = events[-1]
    assert paused.payload["reason"] == "sample_validation"
    assert paused.payload["pause_node_id"] == "node_a"
    assert paused.payload["review_required"]["is_blocking"] is True


def test_timeline_builder_accepts_execution_paused_as_terminal_event():
    events = [
        ExecutionEvent("execution_started", "run1", None, 0, {}),
        ExecutionEvent("node_started", "run1", "A", 10, {}),
        ExecutionEvent("node_completed", "run1", "A", 20, {"status": "partial", "error": "execution paused for review: sample_validation"}),
        ExecutionEvent("execution_paused", "run1", None, 25, {"reason": "sample_validation"}),
    ]

    bundle = ExecutionTimelineBuilder().build(events)
    assert bundle.timeline.duration_ms == 25
    assert bundle.profile.total_nodes == 1
    assert bundle.profile.failed_nodes == 0
    assert bundle.profile.succeeded_nodes == 0
    assert bundle.timeline.node_spans[0].status == "partial"
