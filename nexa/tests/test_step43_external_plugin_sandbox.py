from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from src.platform.external_loader import ExternalPluginLoadError, load_external_plugins


def _write_plugin(tmp_path: Path, plugin_id: str, inject_target: str, inject_key: str, code: str, timeout_ms: int = 50):
    d = tmp_path / plugin_id
    d.mkdir(parents=True)
    (d / "plugin.py").write_text(code, encoding="utf-8")
    manifest = {
        "manifest_version": "1.0",
        "id": plugin_id,
        "type": "provider",
        "entrypoint": "plugin:run",
        "inject": {"target": inject_target, "key": inject_key},
        "determinism": {"required": True},
        "safety": {"timeout_ms": timeout_ms},
    }
    (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return d


def test_step43_external_plugin_sandbox_success(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    _write_plugin(
        plugins_dir,
        "p_ok",
        "providers",
        "x",
        code="""
def run(**kwargs):
    return {"ok": True, "kwargs": kwargs}
""",
        timeout_ms=200,
    )
    loaded = load_external_plugins(plugins_dir=plugins_dir, enabled=True, default_timeout_ms=200)
    p = loaded[("providers", "x")]
    res, val = p.call(a=1)
    assert res.success is True
    assert val["ok"] is True
    assert val["kwargs"]["a"] == 1


def test_step43_external_plugin_sandbox_timeout(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    _write_plugin(
        plugins_dir,
        "p_sleep",
        "providers",
        "y",
        code="""
import time
def run(**kwargs):
    time.sleep(0.2)
    return {"ok": True}
""",
        timeout_ms=10,
    )
    loaded = load_external_plugins(plugins_dir=plugins_dir, enabled=True, default_timeout_ms=50)
    p = loaded[("providers", "y")]
    res, _ = p.call()
    assert res.success is False
    assert res.timeout is True


def test_step43_external_plugin_sandbox_crash(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    _write_plugin(
        plugins_dir,
        "p_crash",
        "providers",
        "z",
        code="""
def run(**kwargs):
    raise RuntimeError("boom")
""",
        timeout_ms=200,
    )
    loaded = load_external_plugins(plugins_dir=plugins_dir, enabled=True, default_timeout_ms=50)
    p = loaded[("providers", "z")]
    res, _ = p.call()
    assert res.success is False
    assert res.timeout is False
    assert res.error is not None


def test_step43_external_plugin_injection_conflict(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    _write_plugin(plugins_dir, "p1", "providers", "x", "def run(**kwargs): return 1", timeout_ms=50)
    _write_plugin(plugins_dir, "p2", "providers", "x", "def run(**kwargs): return 2", timeout_ms=50)

    with pytest.raises(ExternalPluginLoadError):
        load_external_plugins(plugins_dir=plugins_dir, enabled=True, default_timeout_ms=50)
