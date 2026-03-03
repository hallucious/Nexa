from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

# Local, dependency-free SemVer parsing/comparison (major.minor.patch only).
def _parse_semver(v: str) -> Tuple[int, int, int]:
    parts = v.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid SemVer (expected MAJOR.MINOR.PATCH): {v!r}")
    try:
        major, minor, patch = (int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception as e:
        raise ValueError(f"Invalid SemVer numeric parts: {v!r}") from e
    if major < 0 or minor < 0 or patch < 0:
        raise ValueError(f"Invalid SemVer (negative): {v!r}")
    return major, minor, patch


def _semver_key(v: str) -> Tuple[int, int, int]:
    return _parse_semver(v)


@dataclass(frozen=True)
class PluginRequires:
    node_exec_min: str
    plugin_contract_min: str


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    plugin_version: str
    description: str
    stages_allowed: Tuple[str, ...]
    default_timeout_ms: int
    side_effects: Tuple[str, ...]
    requires: PluginRequires
    tags: Tuple[str, ...] = ()
    metadata: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        if not isinstance(self.plugin_id, str) or not self.plugin_id.strip():
            raise ValueError("plugin_id must be a non-empty string")
        _parse_semver(self.plugin_version)

        allowed = {"pre", "core", "post"}
        if not self.stages_allowed:
            raise ValueError("stages_allowed must be non-empty")
        if any(s not in allowed for s in self.stages_allowed):
            raise ValueError("stages_allowed contains invalid stage")

        if not isinstance(self.default_timeout_ms, int) or self.default_timeout_ms <= 0:
            raise ValueError("default_timeout_ms must be a positive integer")

        _parse_semver(self.requires.node_exec_min)
        _parse_semver(self.requires.plugin_contract_min)

        # metadata must be JSON-serializable conceptually; we only enforce dict or None here.
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict or None")


@dataclass(frozen=True)
class PluginEntry:
    manifest: PluginManifest
    entrypoint: Callable[..., Any]


class PluginRegistry:
    """In-memory, deterministic plugin registry (PLUGIN-REGISTRY v1.0.0)."""

    def __init__(self) -> None:
        # key: (plugin_id, plugin_version)
        self._entries: Dict[Tuple[str, str], PluginEntry] = {}

    def register(self, *, manifest: PluginManifest, entrypoint: Callable[..., Any]) -> None:
        manifest.validate()
        key = (manifest.plugin_id, manifest.plugin_version)
        if key in self._entries:
            raise ValueError("Duplicate (plugin_id, plugin_version) registration")
        self._entries[key] = PluginEntry(manifest=manifest, entrypoint=entrypoint)

    def resolve(self, *, plugin_id: str, version: str) -> PluginEntry:
        if version == "latest":
            versions = [v for (pid, v) in self._entries.keys() if pid == plugin_id]
            if not versions:
                raise KeyError(f"Plugin not found: {plugin_id!r}")
            latest_v = sorted(versions, key=_semver_key)[-1]
            return self._entries[(plugin_id, latest_v)]

        # exact version
        _parse_semver(version)
        key = (plugin_id, version)
        if key not in self._entries:
            raise KeyError(f"Plugin not found: {plugin_id!r} {version!r}")
        return self._entries[key]

    def list_manifests(self, *, plugin_id: Optional[str] = None) -> List[PluginManifest]:
        mans: List[PluginManifest] = []
        for (pid, _), entry in self._entries.items():
            if plugin_id is None or plugin_id == pid:
                mans.append(entry.manifest)
        # deterministic ordering
        mans.sort(key=lambda m: (m.plugin_id, _semver_key(m.plugin_version)))
        return mans

    @staticmethod
    def is_compatible(*, current_node_exec: str, current_plugin_contract: str, requires: PluginRequires) -> bool:
        return _semver_key(current_node_exec) >= _semver_key(requires.node_exec_min) and _semver_key(current_plugin_contract) >= _semver_key(requires.plugin_contract_min)
