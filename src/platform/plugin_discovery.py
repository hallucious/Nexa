from __future__ import annotations

"""Filesystem discovery for the hybrid plugin system (v0.1).

We deliberately keep discovery dumb and predictable:
- Only looks under src/platform
- Only considers files that end with *_plugin.py
- plugin_id is the filename stem without the suffix
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class DiscoveredPlugin:
    plugin_id: str
    path: Path


def discover_platform_plugins(repo_root: Path) -> List[DiscoveredPlugin]:
    platform_dir = repo_root / "src" / "platform"
    out: List[DiscoveredPlugin] = []
    if not platform_dir.exists():
        return out

    for p in sorted(platform_dir.glob("*_plugin.py")):
        name = p.name
        plugin_id = name[: -len("_plugin.py")]
        out.append(DiscoveredPlugin(plugin_id=plugin_id, path=p))
    return out


def discovered_ids(repo_root: Path) -> set[str]:
    return {d.plugin_id for d in discover_platform_plugins(repo_root)}


def discovered_paths(repo_root: Path) -> Dict[str, Path]:
    return {d.plugin_id: d.path for d in discover_platform_plugins(repo_root)}
