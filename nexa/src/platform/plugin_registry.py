from __future__ import annotations

"""Platform plugin registry.

This module is the explicit source of truth for which platform plugins are
considered part of the stable surface.

Hybrid policy:
- Discovery (scan) finds candidate *_plugin.py files under src/platform/.
- Registry (this file) lists the plugins that are allowed/expected.
- Tests compare the two to catch orphan files and missing registrations.

Add new engine-native plugin entries here as they are introduced.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class PluginContract:
    plugin_id: str
    module: str
    required_symbols: Sequence[str]


def registry() -> Dict[str, PluginContract]:
    """Return the platform plugin registry.

    plugin_id convention: filename stem of *_plugin.py (without suffix).
    """
    items: Iterable[PluginContract] = ()

    out: Dict[str, PluginContract] = {i.plugin_id: i for i in items}
    return out


def ids() -> set[str]:
    return set(registry().keys())


def by_id(plugin_id: str) -> PluginContract:
    r = registry()
    return r[plugin_id]


def as_mapping() -> Mapping[str, PluginContract]:
    return registry()
