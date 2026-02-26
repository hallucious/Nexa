from __future__ import annotations

from pathlib import Path

import pytest

from src.platform.injection_registry import (
    InjectionRegistry,
    InjectionRegistryError,
    InjectionSpec,
    InjectionHandle,
)
from src.pipeline.observability import read_observability_events


class _DummyProvider:
    def generate_text(self, prompt, temperature=0.0, max_output_tokens=10):
        return (f"echo:{prompt}", {"ok": True}, None)


def test_step41b2_registry_duplicate_rejected():
    reg = InjectionRegistry()
    reg.register(spec=InjectionSpec(target="providers", key="x", version="1.0.0"), impl=_DummyProvider())
    with pytest.raises(InjectionRegistryError):
        reg.register(spec=InjectionSpec(target="providers", key="x", version="1.0.0"), impl=_DummyProvider())


def test_step41b2_registry_version_mismatch_rejected():
    reg = InjectionRegistry()
    reg.register(spec=InjectionSpec(target="providers", key="x", version="1.0.0"), impl=_DummyProvider())
    with pytest.raises(InjectionRegistryError):
        reg.register(spec=InjectionSpec(target="providers", key="x", version="2.0.0"), impl=_DummyProvider())


def test_step41b2_handle_writes_injection_call_observability(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)

    reg = InjectionRegistry(run_dir=str(run_dir))
    reg.register(spec=InjectionSpec(target="providers", key="x", version="1.0.0", determinism_required=True), impl=_DummyProvider())

    h = reg.get(target="providers", key="x")
    res, _val = h.call(prompt="hi", temperature=0.0, max_output_tokens=10)

    assert res.success is True
    events = read_observability_events(run_dir=str(run_dir))
    assert any(e.get("event") == "INJECTION_CALL" and e.get("target") == "providers" and e.get("key") == "x" for e in events)


def test_step41b2_handle_supports_positional_prompt(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True)

    h = InjectionHandle(spec=InjectionSpec(target="providers", key="x", version="1.0.0"), impl=_DummyProvider(), run_dir=str(run_dir))
    res, val = h.call(__args=("hi",), temperature=0.0, max_output_tokens=10)
    assert res.success is True
    assert isinstance(val, tuple) and val[0] == "echo:hi"
