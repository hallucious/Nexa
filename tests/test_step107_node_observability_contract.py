from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor
from pathlib import Path
import json


class DummyProvider:
    def execute(self, request):
        return {"output": f"echo:{request.prompt}", "trace": {"provider": "dummy"}}


def test_step107_node_observability_contract(tmp_path):
    obs = tmp_path / "OBSERVABILITY.jsonl"

    registry = ProviderRegistry()
    registry.register("__legacy_provider__", DummyProvider())
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        observability_file=str(obs),
    )

    node = {"id": "n1", "prompt": "hello {name}"}
    state = {"name": "world"}

    result = runtime.execute(node, state)

    assert result.node_id == "n1"
    assert result.output == "echo:hello world"

    lines = obs.read_text().strip().splitlines()
    assert len(lines) == 1

    data = json.loads(lines[0])
    assert data["node_id"] == "n1"
    assert data["provider"] == "dummy"
