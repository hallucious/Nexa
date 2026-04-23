
from src.providers.legacy_provider_result import ProviderResult
from src.providers.legacy_provider_trace import ProviderTrace


def test_step102_provider_result_basic():
    trace = ProviderTrace()
    r = ProviderResult(
        text="hello",
        raw_response={"id": 1},
        provider_name="openai",
        latency_ms=120.5,
        trace=trace,
    )

    assert r.text == "hello"
    assert r.provider_name == "openai"
    assert r.latency_ms == 120.5
    assert r.trace is trace
