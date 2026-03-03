from __future__ import annotations

import time

from src.platform.plugin import Plugin, PluginResult, safe_execute_plugin


class _OkPlugin(Plugin):
    name = "ok"

    def execute(self, **kwargs):
        return PluginResult(success=True, output={"ok": True}, error=None, latency_ms=0)


class _CrashPlugin(Plugin):
    name = "crash"

    def execute(self, **kwargs):
        raise RuntimeError("boom")


class _SleepPlugin(Plugin):
    name = "sleep"

    def execute(self, **kwargs):
        time.sleep(0.02)
        return PluginResult(success=True, output={"ok": True}, error=None, latency_ms=0)


def test_step78_plugin_result_has_metrics_and_data_alias():
    r = PluginResult(success=True, output={"x": 1}, error=None, latency_ms=12)
    assert r.data == {"x": 1}
    assert isinstance(r.metrics, dict)
    assert r.metrics["latency_ms"] == 12


def test_step78_safe_execute_sets_stage_on_success():
    p = _OkPlugin()
    r = safe_execute_plugin(plugin=p, timeout_ms=1000, stage="PRE")
    assert r.success is True
    assert r.stage == "PRE"
    assert r.reason_code is None


def test_step78_safe_execute_maps_timeout_reason_code():
    p = _SleepPlugin()
    r = safe_execute_plugin(plugin=p, timeout_ms=1, stage="CORE")
    assert r.success is False
    assert r.error == "TIMEOUT"
    assert r.reason_code == "PLUGIN.timeout"
    assert r.stage == "CORE"


def test_step78_safe_execute_maps_crash_reason_code():
    p = _CrashPlugin()
    r = safe_execute_plugin(plugin=p, timeout_ms=1000, stage="POST")
    assert r.success is False
    assert r.reason_code == "SYSTEM.unexpected_exception"
    assert r.stage == "POST"
