from __future__ import annotations

from src.engine.execution_event import ExecutionEvent
from src.engine.execution_event_emitter import ExecutionEventEmitter
from src.engine.node_execution_runtime import Artifact, NodeExecutionRuntime, ReviewRequiredPause
from src.platform.plugin_result import PluginResult


class DummyProviderExecutor:
    def execute(self, request):
        raise RuntimeError("not used in this test")


def test_execution_event_now_builds_event():
    event = ExecutionEvent.now(
        "node_started",
        {"x": 1},
        execution_id="exec-1",
        node_id="node-1",
    )

    assert event.type == "node_started"
    assert event.execution_id == "exec-1"
    assert event.node_id == "node-1"
    assert event.payload == {"x": 1}
    assert isinstance(event.timestamp_ms, int)


def test_execution_event_emitter_collects_events(tmp_path):
    event_file = tmp_path / "events.jsonl"
    emitter = ExecutionEventEmitter(str(event_file))

    emitter.emit(
        ExecutionEvent.now(
            "warning",
            {"message": "x"},
            execution_id="exec-2",
            node_id="n1",
        )
    )

    events = emitter.get_events()
    assert len(events) == 1
    assert events[0].type == "warning"
    assert events[0].execution_id == "exec-2"
    assert event_file.exists()


def test_runtime_emits_artifact_preview_event():
    runtime = NodeExecutionRuntime(
        provider_executor=DummyProviderExecutor(),
        plugin_registry={},
        event_emitter=ExecutionEventEmitter(event_file=None),
    )
    runtime.set_execution_id("exec-preview")

    artifacts = [
        Artifact(
            type="preview",
            name="sample_preview",
            data={"samples": [1, 2, 3]},
            metadata={"source": "test"},
        )
    ]

    runtime._emit_artifact_preview_events("node-a", artifacts)

    events = runtime.get_execution_events()
    assert len(events) == 1
    assert events[0].type == "artifact_preview"
    assert events[0].execution_id == "exec-preview"
    assert events[0].node_id == "node-a"
    assert events[0].payload["artifact_name"] == "sample_preview"


def test_runtime_emits_progress_event_from_plugin_result():
    runtime = NodeExecutionRuntime(
        provider_executor=DummyProviderExecutor(),
        plugin_registry={},
        event_emitter=ExecutionEventEmitter(event_file=None),
    )
    runtime.set_execution_id("exec-progress")

    result = PluginResult(
        output={"result": "ok"},
        trace={"progress": {"processed": 3, "total": 10}},
    )

    runtime._emit_progress_event_from_plugin_result(
        node_id="node-b",
        plugin_id="demo.plugin",
        plugin_result=result,
    )

    events = runtime.get_execution_events()
    assert len(events) == 1
    assert events[0].type == "progress"
    assert events[0].execution_id == "exec-progress"
    assert events[0].node_id == "node-b"
    assert events[0].payload["plugin_id"] == "demo.plugin"
    assert events[0].payload["processed"] == 3
    assert events[0].payload["total"] == 10

def test_artifact_preview_event_marks_preview_as_non_final_truth():
    runtime = NodeExecutionRuntime(
        provider_executor=DummyProviderExecutor(),
        plugin_registry={},
        event_emitter=ExecutionEventEmitter(event_file=None),
    )
    runtime.set_execution_id("exec-preview-safe")

    artifact = Artifact(
        type="preview",
        name="partial_summary",
        data={"chunks": ["a", "b"]},
        metadata={"stage": "intermediate"},
    )

    payload = runtime._build_artifact_preview_payload(artifact)

    assert payload["artifact_name"] == "partial_summary"
    assert payload["artifact_type"] == "preview"
    assert payload["is_final_artifact"] is False
    assert payload["preview_kind"] == "mapping"
    assert payload["preview_summary"] == "mapping[1]"


def test_runtime_emits_review_required_event_from_plugin_result():
    runtime = NodeExecutionRuntime(
        provider_executor=DummyProviderExecutor(),
        plugin_registry={},
        event_emitter=ExecutionEventEmitter(event_file=None),
    )
    runtime.set_execution_id("exec-review")

    result = PluginResult(
        output={"result": "needs-review"},
        trace={
            "review_required": {
                "reason": "sample_validation",
                "sample_size": 5,
            }
        },
    )

    runtime._emit_review_required_event_from_plugin_result(
        node_id="node-review",
        plugin_id="demo.plugin",
        plugin_result=result,
    )

    events = runtime.get_execution_events()
    assert len(events) == 1
    assert events[0].type == "review_required"
    assert events[0].execution_id == "exec-review"
    assert events[0].node_id == "node-review"
    assert events[0].payload["plugin_id"] == "demo.plugin"
    assert events[0].payload["reason"] == "sample_validation"
    assert events[0].payload["sample_size"] == 5
    assert events[0].payload["is_blocking"] is False


def test_runtime_pauses_for_review_when_review_gate_is_enabled(tmp_path):
    runtime = NodeExecutionRuntime(
        provider_executor=DummyProviderExecutor(),
        plugin_registry={
            "demo.plugin": lambda **kwargs: PluginResult(
                output={"result": "needs-review"},
                trace={
                    "review_required": {
                        "reason": "sample_validation",
                        "sample_size": 3,
                        "is_blocking": True,
                    }
                },
            )
        },
        event_emitter=ExecutionEventEmitter(event_file=None),
        observability_file=str(tmp_path / "obs.jsonl"),
    )
    runtime.set_execution_id("exec-review-gate")

    config = {
        "config_id": "cfg.review.gate",
        "plugins": [
            {
                "plugin_id": "demo.plugin",
                "inputs": {},
            }
        ],
        "runtime_config": {
            "pause_on_review_required": True,
            "write_observability": False,
        },
    }

    try:
        runtime.execute(config, {})
    except ReviewRequiredPause as exc:
        assert exc.node_id == "cfg.review.gate"
        assert exc.payload["reason"] == "sample_validation"
        assert exc.payload["is_blocking"] is True
    else:
        raise AssertionError("expected review-required pause")

    events = runtime.get_execution_events()
    assert [event.type for event in events] == [
        "node_started",
        "review_required",
        "node_completed",
    ]
    completed = events[-1]
    assert completed.payload["status"] == "partial"
    assert completed.payload["error_type"] == "ReviewRequiredPause"
    assert completed.payload["review_required"]["reason"] == "sample_validation"


def test_review_required_payload_contains_minimal_resume_contract():
    runtime = NodeExecutionRuntime(
        provider_executor=DummyProviderExecutor(),
        plugin_registry={},
        event_emitter=ExecutionEventEmitter(event_file=None),
    )

    payload = runtime._extract_review_required_payload(
        plugin_id="demo.plugin",
        plugin_result=PluginResult(
            output={"x": 1},
            trace={"review_required": {"reason": "human_check"}},
        ),
    )

    assert payload is not None
    assert payload["resume"]["can_resume"] is True
    assert payload["resume"]["resume_strategy"] == "restart_from_node"
    assert payload["resume"]["requires_revalidation"] == [
        "structural_validation",
        "determinism_pre_validation",
    ]
