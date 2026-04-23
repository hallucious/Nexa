from __future__ import annotations

import pytest

from src.platform.plugin_version_registry import PluginManifest, PluginRegistry, PluginRequires


def _mk_manifest(pid: str, ver: str) -> PluginManifest:
    return PluginManifest(
        plugin_id=pid,
        plugin_version=ver,
        description="d",
        stages_allowed=("core",),
        default_timeout_ms=100,
        side_effects=(),
        requires=PluginRequires(node_exec_min="1.0.0", plugin_contract_min="1.0.0"),
    )


def test_register_duplicate_fails():
    r = PluginRegistry()
    m = _mk_manifest("p", "1.0.0")

    def ep(**kwargs):  # pragma: no cover
        return kwargs

    r.register(manifest=m, entrypoint=ep)
    with pytest.raises(ValueError):
        r.register(manifest=m, entrypoint=ep)


def test_resolve_exact_version():
    r = PluginRegistry()
    m = _mk_manifest("p", "1.0.0")

    def ep(**kwargs):  # pragma: no cover
        return kwargs

    r.register(manifest=m, entrypoint=ep)
    e = r.resolve(plugin_id="p", version="1.0.0")
    assert e.manifest.plugin_id == "p"
    assert e.manifest.plugin_version == "1.0.0"


def test_resolve_latest_highest_semver():
    r = PluginRegistry()

    def ep(**kwargs):  # pragma: no cover
        return kwargs

    r.register(manifest=_mk_manifest("p", "1.0.0"), entrypoint=ep)
    r.register(manifest=_mk_manifest("p", "1.2.0"), entrypoint=ep)
    r.register(manifest=_mk_manifest("p", "1.1.5"), entrypoint=ep)

    e = r.resolve(plugin_id="p", version="latest")
    assert e.manifest.plugin_version == "1.2.0"


def test_compatibility_check():
    req = PluginRequires(node_exec_min="1.0.0", plugin_contract_min="1.0.0")
    assert PluginRegistry.is_compatible(current_node_exec="1.0.0", current_plugin_contract="1.0.0", requires=req) is True
    assert PluginRegistry.is_compatible(current_node_exec="0.9.9", current_plugin_contract="1.0.0", requires=req) is False
