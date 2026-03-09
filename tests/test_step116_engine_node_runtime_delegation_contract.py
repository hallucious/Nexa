from src.engine.engine import Engine
from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.engine.types import NodeStatus
from src.platform.provider_registry import ProviderRegistry
from src.platform.provider_executor import ProviderExecutor


class FakeProvider:
    def execute(self, request):
        return {"output": {"answer": "ok", "prompt": request.prompt}, "trace": {"provider": "fake"}}


def test_step116_engine_delegates_to_node_runtime_when_no_handler(tmp_path):
    registry = ProviderRegistry()
    registry.register("__legacy_provider__", FakeProvider())
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        observability_file=str(tmp_path / "obs.jsonl")
    )

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={},
        node_runtime=runtime,
    )

    trace = eng.execute(revision_id="rev116")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n1"].output_snapshot == {"answer": "ok", "prompt": ""}
