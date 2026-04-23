
from src.providers.legacy_provider_trace import ProviderTrace


def test_step101_trace_records_attempt():
    t = ProviderTrace()
    t.record_attempt("openai")
    assert t.attempted_providers == ["openai"]


def test_step101_trace_records_failure():
    t = ProviderTrace()
    t.record_failure("openai", "timeout")
    assert t.failures["openai"] == "timeout"


def test_step101_trace_records_selected():
    t = ProviderTrace()
    t.record_selected("anthropic")
    assert t.selected_provider == "anthropic"
