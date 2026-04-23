import pytest

from src.contracts.confidence_contract import build_assessment
from src.engine.budget_router import decide_route, log_route
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.engine.safety_gate import evaluate_gate
from src.platform.provider_executor import ProviderExecutor
from src.platform.provider_registry import ProviderRegistry
from src.storage.execution_record_api import create_serialized_execution_record_from_circuit_run


class RecordingProvider:
    def __init__(self, name: str):
        self.name = name
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return {
            "output": f"{self.name}:{request.prompt or 'empty'}",
            "trace": {"provider": self.name},
        }


def _runtime(tmp_path, providers):
    registry = ProviderRegistry()
    for provider_id, provider in providers.items():
        registry.register(provider_id, provider)
    return NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        observability_file=str(tmp_path / "obs.jsonl"),
    )


def test_step226_runtime_applies_budget_routing_safety_gate_and_confidence(tmp_path):
    cheap = RecordingProvider("cheap")
    hq = RecordingProvider("hq")
    runtime = _runtime(tmp_path, {"cheap": cheap, "hq": hq})

    config = {
        "config_id": "ec_precision_runtime",
        "node_id": "n1",
        "provider": {
            "provider_id": "cheap",
            "provider_candidates": ["hq", "cheap"],
            "allowed_models": ["hq-model", "cheap-model"],
            "model": "cheap-model",
        },
        "runtime_config": {
            "return_raw_output": True,
            "emit_confidence_artifact": True,
            "budget_routing": {
                "current_budget": 25.0,
                "difficulty_estimate": 0.95,
                "quality_target": 0.95,
                "allowed_providers": ["hq", "cheap"],
                "allowed_models": ["hq-model", "cheap-model"],
                "task_type": "analysis",
            },
            "safety_gate": {
                "allowed_actions": ["provider_execute"],
            },
        },
    }

    result = runtime.execute(config, {"question": "which provider wins"})

    assert result.output == "hq:empty"
    assert len(hq.requests) == 1
    assert len(cheap.requests) == 0
    assert result.trace.precision["routing"]
    assert result.trace.precision["routing"][0]["route_decision"]["selected_provider_id"] == "hq"
    assert result.trace.precision["safety_gates"][0]["status"] == "allow"
    assert result.trace.precision["node_confidence"]["target_ref"] == "node.n1.output"
    assert any(artifact.type == "confidence_assessment" for artifact in result.artifacts)


def test_step226_runtime_blocks_provider_execution_when_safety_gate_blocks(tmp_path):
    blocked = RecordingProvider("blocked")
    runtime = _runtime(tmp_path, {"blocked": blocked})

    config = {
        "config_id": "ec_precision_blocked",
        "node_id": "n1",
        "provider": {
            "provider_id": "blocked",
        },
        "runtime_config": {
            "return_raw_output": True,
            "budget_routing": {
                "current_budget": 5.0,
                "allowed_providers": ["blocked"],
            },
            "safety_gate": {
                "allowed_actions": ["provider_execute"],
                "denied_providers": ["blocked"],
                "data_sensitivity": "restricted",
            },
        },
    }

    with pytest.raises(RuntimeError, match="safety gate"):
        runtime.execute(config, {})

    assert blocked.requests == []


def test_step226_execution_record_projects_precision_summaries_from_trace():
    routing_context = runtime_ctx = None
    from src.contracts.budget_routing_contract import RoutingContext

    routing_context = RoutingContext(
        node_id="n1",
        task_type="analysis",
        current_budget=20.0,
        difficulty_estimate=0.8,
        risk_level="low",
        allowed_providers=["hq"],
        allowed_models=["hq-model"],
    )
    decision = decide_route(routing_context)
    route_log = log_route(decision, routing_context).to_dict()
    gate = evaluate_gate(
        target_ref="node.n1.provider",
        requested_actions=["provider_execute"],
        requested_providers=[decision.selected_provider_id],
    ).to_dict()
    provider_confidence = build_assessment(
        target_ref="node.n1.provider.hq",
        confidence_score=0.76,
        evidence_density_score=0.7,
        explanation="provider path confidence",
    ).to_dict()
    node_confidence = build_assessment(
        target_ref="node.n1.output",
        confidence_score=0.81,
        evidence_density_score=0.72,
        explanation="node confidence",
    ).to_dict()

    payload = create_serialized_execution_record_from_circuit_run(
        {"id": "precision-circuit", "nodes": [{"id": "n1"}]},
        {"n1": {"value": "ok"}},
        execution_id="precision-exec",
        trace={
            "events": ["started", "completed"],
            "node_results": {
                "n1": {
                    "trace": {
                        "precision": {
                            "routing": [route_log],
                            "safety_gates": [gate],
                            "confidence_assessments": [provider_confidence],
                            "node_confidence": node_confidence,
                        }
                    }
                }
            },
        },
    )

    record_node = payload["node_results"]["results"][0]
    assert payload["observability"]["routing_summary"]["route_count"] == 1
    assert payload["observability"]["safety_summary"]["blocked"] is False
    assert payload["observability"]["confidence_summary"]["node_confidence_count"] == 1
    assert record_node["route_summary"]["route_decision"]["selected_provider_id"] == decision.selected_provider_id
    assert record_node["confidence_summary"]["target_ref"] == "node.n1.output"
