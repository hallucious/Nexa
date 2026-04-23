import pytest

from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor


def test_step202_node_runtime_verifier_integration_emits_typed_artifacts_and_trace():
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(ProviderRegistry()),
        plugin_registry={
            "emit": lambda **kwargs: {"output": {"answer": "ok", "reason": "clear answer"}}
        },
    )
    runtime.set_execution_id("run-verifier-ok")

    config = {
        "config_id": "n1",
        "version": "1.0.0",
        "node_id": "n1",
        "plugins": [{"plugin_id": "emit"}],
        "verifier": {
            "verifier_id": "answer_quality",
            "emit_output_artifact": True,
            "modes": [
                {
                    "verifier_type": "structural",
                    "expected_artifact_type": "json_object",
                    "required_keys": ["answer", "reason"],
                },
                {
                    "verifier_type": "requirement",
                    "allow_empty": False,
                },
            ],
        },
    }

    result = runtime.execute(config, {})

    assert result.output == {"answer": "ok", "reason": "clear answer"}
    assert "verifier:pass" in result.trace.events
    assert len(result.trace.verifier_trace) == 1
    assert len(result.trace.typed_artifact_refs) == 2
    artifact_types = [artifact.type for artifact in result.artifacts]
    assert "validation_report" in artifact_types
    assert "json_object" in artifact_types
    events = runtime.get_execution_events()
    assert any(event.type == "verification_completed" for event in events)


def test_step202_node_runtime_verifier_integration_blocks_when_configured():
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(ProviderRegistry()),
        plugin_registry={"emit": lambda **kwargs: {"output": "tiny"}},
    )
    runtime.set_execution_id("run-verifier-fail")

    config = {
        "config_id": "n1",
        "version": "1.0.0",
        "node_id": "n1",
        "plugins": [{"plugin_id": "emit"}],
        "verifier": {
            "verifier_id": "answer_quality",
            "blocking": True,
            "modes": [
                {
                    "verifier_type": "structural",
                    "expected_artifact_type": "json_object",
                    "required_keys": ["answer"],
                }
            ],
        },
    }

    with pytest.raises(ValueError, match="output verification failed"):
        runtime.execute(config, {})

    events = runtime.get_execution_events()
    assert any(event.type == "verification_completed" for event in events)
    assert any(event.type == "node_completed" and event.payload.get("status") == "failed" for event in events)
