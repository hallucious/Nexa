from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_executor import ProviderExecutor
from src.platform.provider_registry import ProviderRegistry
from src.storage.execution_record_api import create_serialized_execution_record_from_circuit_run


class PassThroughProvider:
    def __init__(self, output):
        self.output = output

    def execute(self, request):
        return {"output": self.output, "trace": {"provider": "pass_through"}}


def _runtime(tmp_path, provider):
    registry = ProviderRegistry()
    registry.register("p1", provider)
    return NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        observability_file=str(tmp_path / "obs.jsonl"),
    )


def test_step229_verifier_followup_declares_branch_candidate(tmp_path):
    runtime = _runtime(tmp_path, PassThroughProvider({"score": 1}))
    config = {
        "config_id": "ec_branch_candidate",
        "node_id": "n1",
        "provider": {"provider_id": "p1"},
        "runtime_config": {
            "return_raw_output": True,
        },
        "verifier": {
            "verifier_id": "req_check",
            "modes": [
                {
                    "verifier_type": "structural",
                    "expected_artifact_type": "json_object",
                    "required_keys": ["missing_key"],
                }
            ],
        },
    }

    result = runtime.execute(config, {})

    branch_candidates = result.trace.precision["branch_candidates"]
    assert len(branch_candidates) == 1
    payload = branch_candidates[0]
    assert payload["branch_ref"]["branch_policy"] == "verifier_followup"
    assert payload["recommended_next_step"] == "retry"
    assert payload["target_ref"] == "node.n1.output"
    events = runtime.get_execution_events()
    assert any(event.type == "branch_candidate_declared" for event in events)


def test_step229_execution_record_projects_branch_summary():
    payload = create_serialized_execution_record_from_circuit_run(
        {"id": "branch-circuit", "nodes": [{"id": "n1"}]},
        {"n1": {"value": "retry"}},
        execution_id="branch-exec",
        trace={
            "events": [
                {
                    "type": "branch_candidate_declared",
                    "payload": {
                        "branch_ref": {
                            "branch_id": "b-1",
                            "parent_state_ref": "run:branch-exec",
                            "branch_reason": "missing_key",
                            "branch_policy": "verifier_followup",
                            "created_at": "2026-04-07T00:00:00+00:00",
                            "status": "active",
                        },
                        "target_ref": "node.n1.output",
                        "aggregate_status": "fail",
                        "recommended_next_step": "retry",
                        "blocking_reason_codes": ["missing_key"],
                    },
                }
            ],
            "node_results": {
                "n1": {
                    "status": "error",
                    "trace": {"timings_ms": {"provider_execute": 12.0}},
                }
            },
        },
    )

    summary = payload["observability"]["branch_summary"]
    assert summary["branch_candidate_count"] == 1
    assert summary["branch_ids"] == ["b-1"]
    assert summary["policies"] == ["verifier_followup"]
    assert summary["recommended_next_steps"] == ["retry"]
    assert summary["reason_codes"] == ["missing_key"]
