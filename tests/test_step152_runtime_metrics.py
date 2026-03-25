from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.providers.provider_contract import ProviderResult, ProviderMetrics


class DummyProviderExecutor:
    def execute(self, request):
        return ProviderResult(
            success=True,
            text="ok",
            raw={"output": "ok", "provider_id": request.provider_id},
            error=None,
            reason_code=None,
            metrics=ProviderMetrics(latency_ms=0),
        )


def test_step152_runtime_metrics_collection():
    runtime = NodeExecutionRuntime(
        provider_executor=DummyProviderExecutor(),
        plugin_registry={
            "test": lambda **k: {"x": 1}
        },
    )

    runtime.reset_metrics()

    runtime.record_wave()
    runtime.execute_plugin("test")
    runtime.execute_provider("openai")
    runtime.execute_node("node1", lambda: {"a": 1})

    metrics = runtime.get_metrics()

    assert metrics["wave_count"] == 1
    assert metrics["plugin_calls"] == 1
    assert metrics["provider_calls"] == 1
    assert metrics["executed_nodes"] == 1
