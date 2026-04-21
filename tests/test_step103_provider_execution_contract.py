
from src.providers.legacy_provider_execution import ProviderExecution
from src.providers.legacy_provider_result import ProviderResult
from src.providers.legacy_provider_trace import ProviderTrace


class MockProvider:
    def generate(self, *, prompt, model, trace, **kwargs):
        return ProviderResult(
            text="ok",
            raw_response={"mock": True},
            provider_name="mock",
            latency_ms=10,
            trace=trace,
        )


def test_step103_provider_execution_bridge():
    exec_layer = ProviderExecution(MockProvider())

    result = exec_layer.execute(
        prompt="hello",
        model="mock-model",
        trace=ProviderTrace()
    )

    assert result.text == "ok"
    assert result.provider_name == "mock"
