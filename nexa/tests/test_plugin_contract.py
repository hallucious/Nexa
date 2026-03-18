from __future__ import annotations

from src.platform.plugin import DummyEchoPlugin, PluginResult


def test_dummy_echo_plugin_success():
    plugin = DummyEchoPlugin()
    result = plugin.execute(a=1, b="x")

    assert isinstance(result, PluginResult)
    assert result.success is True
    assert result.output == {"echo": {"a": 1, "b": "x"}}
    assert result.error is None
    assert isinstance(result.latency_ms, int)
