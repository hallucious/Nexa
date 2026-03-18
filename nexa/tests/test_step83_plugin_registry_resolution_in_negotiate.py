from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from src.platform.capability_negotiation import negotiate
from src.platform.plugin import DummyEchoPlugin
from src.platform.plugin_version_registry import (
    PluginEntry,
    PluginManifestV1,
    PluginRequires,
    PluginVersionRegistry,
)


@dataclass
class _Ctx:
    run_dir: str = "."
    meta: Any = None
    context: Dict[str, Any] = None  # type: ignore[assignment]
    providers: Dict[str, Any] = None  # type: ignore[assignment]
    plugins: Dict[str, Any] = None  # type: ignore[assignment]


def test_negotiate_resolves_plugin_ref_via_registry_when_present():
    reg = PluginVersionRegistry()
    reg.register(
        entry=PluginEntry(
            manifest=PluginManifestV1(
                plugin_id="dummy_echo",
                plugin_version="1.0.0",
                description="test",
                stages_allowed=["pre", "core", "post"],
                default_timeout_ms=1000,
                side_effects=[],
                requires=PluginRequires(node_exec_min="1.0.0", plugin_contract_min="1.0.0"),
            ),
            entrypoint=DummyEchoPlugin,
            factory=DummyEchoPlugin,
        )
    )

    ctx = _Ctx(
        context={"plugin_registry": reg},
        providers={},
        plugins={"echo": ("dummy_echo", "1.0.0")},
    )

    res = negotiate(
        gate_id="G_TEST",
        capability="echo",
        ctx=ctx,
        priority_chain=[("plugins", "echo")],
        required=True,
        emit_observability=False,
    )

    assert res.missing is False
    assert isinstance(res.selected, DummyEchoPlugin)


def test_negotiate_returns_none_for_unresolvable_ref():
    reg = PluginVersionRegistry()
    ctx = _Ctx(
        context={"plugin_registry": reg},
        providers={},
        plugins={"echo": ("dummy_echo", "1.0.0")},
    )

    res = negotiate(
        gate_id="G_TEST",
        capability="echo",
        ctx=ctx,
        priority_chain=[("plugins", "echo")],
        required=False,
        emit_observability=False,
    )
    assert res.selected is None
    assert res.missing is True
