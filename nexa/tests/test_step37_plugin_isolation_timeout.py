import time

from src.platform.safe_exec import safe_call
from src.platform.worker import ProviderTextWorker
from src.platform.plugin import Plugin, PluginResult, safe_execute_plugin


class _SleepProvider:
    def generate_text(self, *, prompt: str, temperature: float, max_output_tokens: int, instructions=None):
        time.sleep(0.02)
        return "ok", {"prompt": prompt}, None


class _SleepPlugin(Plugin):
    name = "sleep"

    def execute(self, **kwargs):
        time.sleep(0.02)
        return PluginResult(success=True, output={"ok": True}, error=None, latency_ms=0)


def test_step37_worker_timeout_returns_fast():
    w = ProviderTextWorker(name="p", provider=_SleepProvider())
    res = w.generate_text(prompt="hi", timeout_ms=1)
    assert res.success is False
    assert res.error == "TIMEOUT"


def test_step37_plugin_timeout_returns_fast():
    p = _SleepPlugin()
    res = safe_execute_plugin(plugin=p, timeout_ms=1)
    assert res.success is False
    assert res.error == "TIMEOUT"


def test_step37_safe_call_no_timeout_ok():
    r = safe_call(fn=lambda: 123, timeout_ms=None)
    assert r.ok is True
    assert r.value == 123
