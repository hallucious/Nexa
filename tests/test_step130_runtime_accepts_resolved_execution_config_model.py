from pathlib import Path
import json

from src.engine.execution_config_hash import generate_execution_config_id
from src.engine.graph_execution_runtime import GraphExecutionRuntime
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.engine.node_spec_resolver import NodeSpecResolver
from src.platform.execution_config_registry import ExecutionConfigRegistry


class ProviderStub:
    def execute(self, prompt):
        return {"answer": "ok", "trace": {"provider": "stub"}}


def test_step130_runtime_accepts_resolved_execution_config_model(tmp_path: Path):
    registry_root = tmp_path / "registry" / "execution_configs"
    payload = {
        "version": "1.0.0",
        "provider_ref": "provider.stub",
        "output_mapping": {"answer": "answer"},
    }
    payload["config_id"] = generate_execution_config_id(payload)

    config_dir = registry_root / payload["config_id"]
    config_dir.mkdir(parents=True)
    (config_dir / "1.0.0.json").write_text(json.dumps(payload), encoding="utf-8")

    runtime = NodeExecutionRuntime(provider_execution=ProviderStub())
    resolver = NodeSpecResolver(ExecutionConfigRegistry(root=registry_root))
    graph = GraphExecutionRuntime(node_runtime=runtime, node_spec_resolver=resolver)

    result = graph.execute(
        circuit={
            "nodes": [
                {"id": "n1", "execution_config_ref": payload["config_id"]},
            ],
            "edges": [],
        },
        state={},
    )

    assert result.trace.node_sequence == ["n1"]
    assert result.trace.node_outputs["n1"] == {"answer": "ok"}
