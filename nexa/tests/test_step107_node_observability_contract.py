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
    registry.register("dummy", DummyProvider())
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        observability_file=str(obs),
    )

    config = {
        "config_id": "n1",
        "node_id": "n1",
        "provider_ref": "dummy",
        "runtime_config": {
            "return_raw_output": True,
            "write_observability": True,
        },
    }
    state = {"name": "world"}

    result = runtime.execute(config, state)

    assert result.node_id == "n1"

    lines = obs.read_text().strip().splitlines()
    assert len(lines) == 1

    data = json.loads(lines[0])
    assert data["node_id"] == "n1"
    assert data["provider"] == "dummy"
