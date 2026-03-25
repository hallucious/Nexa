from __future__ import annotations

from src.engine.node_execution_runtime import NodeExecutionRuntime
from src.platform.provider_executor import ProviderExecutor
from src.platform.provider_registry import ProviderRegistry
from src.providers.provider_contract import ProviderResult as CanonicalProviderResult


class LegacyDictProvider:
    def execute(self, request):
        return {
            "output": None,
            "structured": {"answer": "ok"},
            "trace": {"provider": "legacy"},
            "metrics": {"latency_ms": 12},
        }


class CanonicalEnvelopeProvider:
    def execute(self, request):
        return CanonicalProviderResult(
            success=True,
            text="hello",
            raw={
                "output": "hello",
                "trace": {"provider": "canonical"},
                "artifacts": [],
            },
            error=None,
            reason_code=None,
            metrics={"latency_ms": 7},
        )


def test_step191_provider_executor_normalizes_legacy_dict_to_canonical():
    registry = ProviderRegistry()
    registry.register("legacy", LegacyDictProvider())
    executor = ProviderExecutor(registry)

    from src.contracts.provider_contract import ProviderRequest

    result = executor.execute(
        ProviderRequest(
            provider_id="legacy",
            prompt="hi",
            context={},
            options={},
            metadata={},
        )
    )

    assert result.success is True
    assert result.text is None
    assert result.raw["structured"]["answer"] == "ok"
    assert result.metrics.latency_ms == 12


def test_step191_runtime_consumes_canonical_provider_result_shape(tmp_path):
    registry = ProviderRegistry()
    registry.register("canonical", CanonicalEnvelopeProvider())
    runtime = NodeExecutionRuntime(
        provider_executor=ProviderExecutor(registry),
        observability_file=str(tmp_path / "obs.jsonl"),
    )

    config = {
        "config_id": "ec_provider_canonical",
        "provider_ref": "canonical",
        "runtime_config": {"return_raw_output": True},
    }

    result = runtime.execute(config, {})

    assert result.output == "hello"
    assert result.trace.provider_trace["provider"] == "canonical"
