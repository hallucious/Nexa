from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


# -------------------------
# SemVer utilities (v1 minimal)
# -------------------------

def _parse_semver(v: str) -> Tuple[int, int, int]:
    """Parse 'MAJOR.MINOR.PATCH' (pre-release/build ignored for v1)."""
    if not isinstance(v, str):
        raise TypeError("version must be a string")
    core = v.split("-", 1)[0].split("+", 1)[0]
    parts = core.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"invalid SemVer: {v}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def _semver_ge(a: str, b: str) -> bool:
    return _parse_semver(a) >= _parse_semver(b)


def _semver_key(v: str) -> Tuple[int, int, int]:
    return _parse_semver(v)


# -------------------------
# Contract types
# -------------------------

@dataclass(frozen=True)
class PluginRequires:
    node_exec_min: str
    plugin_contract_min: str


@dataclass(frozen=True)
class PluginManifestV1:
    plugin_id: str
    plugin_version: str  # SemVer
    description: str
    stages_allowed: Sequence[str]  # accept list/tuple
    default_timeout_ms: int
    side_effects: Sequence[str]  # accept list/tuple
    requires: PluginRequires
    tags: Optional[Sequence[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        if not self.plugin_id or not isinstance(self.plugin_id, str):
            raise ValueError("plugin_id must be a non-empty string")
        _parse_semver(self.plugin_version)

        allowed = {"pre", "core", "post"}
        if not isinstance(self.stages_allowed, (list, tuple)) or len(self.stages_allowed) == 0:
            raise ValueError("stages_allowed must be a non-empty list/tuple")
        if any(s not in allowed for s in self.stages_allowed):
            raise ValueError("stages_allowed contains invalid stage")

        if not isinstance(self.default_timeout_ms, int) or self.default_timeout_ms <= 0:
            raise ValueError("default_timeout_ms must be a positive int")

        if not isinstance(self.side_effects, (list, tuple)):
            raise ValueError("side_effects must be a list/tuple")

        if not isinstance(self.requires, PluginRequires):
            raise ValueError("requires must be PluginRequires")
        _parse_semver(self.requires.node_exec_min)
        _parse_semver(self.requires.plugin_contract_min)


# Backward-compatible public name expected by Step82 tests.
PluginManifest = PluginManifestV1


@dataclass(frozen=True)
class PluginRef:
    plugin_id: str
    plugin_version: str  # SemVer or "latest" (request-side)

    @classmethod
    def latest(cls, plugin_id: str) -> "PluginRef":
        return cls(plugin_id=plugin_id, plugin_version="latest")


@dataclass(frozen=True)
class PluginEntry:
    manifest: PluginManifestV1
    entrypoint: Callable[..., Any]
    factory: Optional[Callable[[], Any]] = None


class PluginRegistryError(ValueError):
    pass


# -------------------------
# Registry implementation
# -------------------------

class PluginVersionRegistry:
    """Versioned registry for plugins.

    Compatibility targets (per existing tests):
    - register(manifest=..., entrypoint=..., factory=...)
    - register(entry=PluginEntry(...))
    - resolve(plugin_id=..., version=...)
    - list(plugin_id=None)
    - is_compatible(current_node_exec=..., current_plugin_contract=..., requires=...)
    """

    def __init__(self) -> None:
        self._entries: Dict[Tuple[str, str], PluginEntry] = {}

    @staticmethod
    def is_compatible(
        *,
        current_node_exec: str,
        current_plugin_contract: str,
        requires: PluginRequires,
    ) -> bool:
        return _semver_ge(current_node_exec, requires.node_exec_min) and _semver_ge(
            current_plugin_contract, requires.plugin_contract_min
        )

    def register(
        self,
        *,
        manifest: Optional[PluginManifestV1] = None,
        entrypoint: Optional[Callable[..., Any]] = None,
        factory: Optional[Callable[[], Any]] = None,
        entry: Optional[PluginEntry] = None,
    ) -> None:
        # Support Step83 style: register(entry=PluginEntry(...))
        if entry is not None:
            if not isinstance(entry, PluginEntry):
                raise TypeError("entry must be PluginEntry")
            manifest = entry.manifest
            entrypoint = entry.entrypoint
            factory = entry.factory

        if manifest is None or entrypoint is None:
            raise TypeError("register requires either entry=... or (manifest=..., entrypoint=...)")

        if not isinstance(manifest, PluginManifestV1):
            raise TypeError("manifest must be PluginManifestV1")
        manifest.validate()

        key = (manifest.plugin_id, manifest.plugin_version)
        if key in self._entries:
            raise PluginRegistryError("duplicate plugin registration")

        if not callable(entrypoint):
            raise TypeError("entrypoint must be callable")

        self._entries[key] = PluginEntry(manifest=manifest, entrypoint=entrypoint, factory=factory)

    def _latest_version(self, plugin_id: str) -> str:
        versions = [v for (pid, v) in self._entries.keys() if pid == plugin_id]
        if not versions:
            raise KeyError(f"plugin_id not found: {plugin_id}")
        return max(versions, key=_semver_key)

    def resolve(self, *, plugin_id: str, version: str) -> PluginEntry:
        if version == "latest":
            version = self._latest_version(plugin_id)
        key = (plugin_id, version)
        if key not in self._entries:
            raise KeyError(f"plugin not found: {plugin_id}@{version}")
        return self._entries[key]

    def list(self, *, plugin_id: Optional[str] = None) -> List[PluginManifestV1]:
        if plugin_id is None:
            return [e.manifest for e in self._entries.values()]
        return [e.manifest for (pid, _), e in self._entries.items() if pid == plugin_id]


# Backward-compatible public name expected by Step82 tests.
PluginRegistry = PluginVersionRegistry


__all__ = [
    "PluginRequires",
    "PluginManifestV1",
    "PluginManifest",
    "PluginEntry",
    "PluginRegistryError",
    "PluginRef",
    "PluginVersionRegistry",
    "PluginRegistry",
]
