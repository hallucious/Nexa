from __future__ import annotations

"""Hybrid plugin wiring (v0.1).

This module is the *explicit* source of truth for which platform plugins are
considered "official".

Hybrid policy:
- Discovery (scan) finds candidate *_plugin.py files.
- Registry (this file) lists the plugins that are allowed/expected.
- Tests compare the two so we catch:
  * orphan plugin files (file exists but not registered)
  * missing registrations (registered but file missing)
  * contract drift (missing entrypoint symbol)

Important: Not every gate must have a plugin. Only registered plugins are
considered part of the stable surface.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class PluginContract:
    plugin_id: str
    module: str
    required_symbols: Sequence[str]


def registry() -> Dict[str, PluginContract]:
    """Return the v0.1 platform plugin registry.

    plugin_id convention: filename stem of *_plugin.py (without suffix).
    """

    items: Iterable[PluginContract] = (
        PluginContract(
            plugin_id="fact_check",
            module="src.platform.fact_check_plugin",
            required_symbols=("resolve_fact_check_plugin", "FactCheckPlugin"),
        ),
        PluginContract(
            plugin_id="g1_design",
            module="src.platform.g1_design_plugin",
            required_symbols=("run_g1_design_plugin",),
        ),
        PluginContract(
            plugin_id="g2_continuity",
            module="src.platform.g2_continuity_plugin",
            required_symbols=("resolve_g2_continuity_plugin",),
        ),
        PluginContract(
            plugin_id="g3_fact_audit",
            module="src.platform.g3_fact_audit_plugin",
            required_symbols=("resolve_fact_check_plugin",),
        ),
        PluginContract(
            plugin_id="g4_self_check",
            module="src.platform.g4_self_check_plugin",
            required_symbols=("run_g4_self_check_plugin",),
        ),
        PluginContract(
            plugin_id="g5_implement_test",
            module="src.platform.g5_implement_test_plugin",
            required_symbols=("resolve_g5_exec_plugin",),
        ),
        PluginContract(
            plugin_id="g6_counterfactual",
            module="src.platform.g6_counterfactual_plugin",
            required_symbols=("resolve_g6_counterfactual_plugin",),
        ),
        PluginContract(
            plugin_id="g7_final_review",
            module="src.platform.g7_final_review_plugin",
            required_symbols=("resolve_g7_final_review_plugin",),
        ),
    )

    out: Dict[str, PluginContract] = {i.plugin_id: i for i in items}
    # Defensive: ensure unique keys.
    if len(out) != len(tuple(items)):
        raise ValueError("Duplicate plugin_id in registry")
    return out


def ids() -> set[str]:
    return set(registry().keys())


def by_id(plugin_id: str) -> PluginContract:
    r = registry()
    return r[plugin_id]


def as_mapping() -> Mapping[str, PluginContract]:
    return registry()
