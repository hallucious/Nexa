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


import importlib
from typing import Any, Optional, Tuple

from src.platform.version import PLATFORM_API_VERSION


@dataclass(frozen=True)
class PluginManifest:
    manifest_version: str
    plugin_id: str
    plugin_type: str
    entrypoint: str
    inject_target: str
    inject_key: str
    determinism_required: bool
    requires_platform_api: str


def _parse_entrypoint(ep: str) -> Tuple[str, str]:
    if ":" not in ep:
        raise ValueError(f"Invalid entrypoint (expected module:symbol): {ep!r}")
    mod, sym = ep.split(":", 1)
    if not mod or not sym:
        raise ValueError(f"Invalid entrypoint (expected module:symbol): {ep!r}")
    return mod, sym


def _import_entrypoint_callable(ep: str) -> Any:
    mod, sym = _parse_entrypoint(ep)
    m = importlib.import_module(mod)
    fn = getattr(m, sym, None)
    if fn is None or not callable(fn):
        raise ValueError(f"Entrypoint not callable: {ep!r}")
    return fn


def _validate_inject(target: str, key: str) -> None:
    if target not in {"providers", "plugins", "context.plugins"}:
        raise ValueError(f"Invalid inject.target: {target!r}")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("Invalid inject.key (must be non-empty string)")


def _validate_requires_platform_api(range_expr: str) -> None:
    # Minimal, deterministic check.
    # We only enforce that the current PLATFORM_API_VERSION is within the declared
    # inclusive lower bound and exclusive upper bound for patterns like:
    #   ">=0.1,<2.0"
    # This is intentionally simple to avoid adding dependencies.
    if not isinstance(range_expr, str) or not range_expr:
        raise ValueError("requires.platform_api must be a non-empty string")

    parts = [p.strip() for p in range_expr.split(",") if p.strip()]
    ge = None
    lt = None
    for p in parts:
        if p.startswith(">="):
            ge = p[2:].strip()
        elif p.startswith("<"):
            lt = p[1:].strip()

    def _to_tuple(v: str) -> Tuple[int, ...]:
        return tuple(int(x) for x in v.split("."))

    cur = _to_tuple(PLATFORM_API_VERSION)
    if ge is not None and cur < _to_tuple(ge):
        raise ValueError(
            f"Platform API version {PLATFORM_API_VERSION} is below required {ge}"
        )
    if lt is not None and cur >= _to_tuple(lt):
        raise ValueError(
            f"Platform API version {PLATFORM_API_VERSION} is not below required {lt}"
        )


def load_platform_plugin_manifests(repo_root: Path) -> List[PluginManifest]:
    """Load and validate PLUGIN_MANIFEST from each discovered plugin module."""
    manifests: List[PluginManifest] = []
    seen_inject: set[tuple[str, str]] = set()

    for d in discover_platform_plugins(repo_root):
        module_name = f"src.platform.{d.plugin_id}_plugin"
        m = importlib.import_module(module_name)

        raw = getattr(m, "PLUGIN_MANIFEST", None)
        if raw is None or not isinstance(raw, dict):
            raise ValueError(f"Missing PLUGIN_MANIFEST in {module_name}")

        # Required fields
        manifest_version = raw.get("manifest_version")
        plugin_id = raw.get("id")
        plugin_type = raw.get("type")
        entrypoint = raw.get("entrypoint")
        inject = raw.get("inject") or {}
        inject_target = inject.get("target")
        inject_key = inject.get("key")
        determinism = raw.get("determinism") or {}
        determinism_required = bool(determinism.get("required"))
        requires = raw.get("requires") or {}
        requires_platform_api = requires.get("platform_api")

        if manifest_version != "1.0":
            raise ValueError(
                f"{module_name}: manifest_version must be '1.0' (got {manifest_version!r})"
            )
        if plugin_id != d.plugin_id:
            raise ValueError(
                f"{module_name}: manifest id mismatch (expected {d.plugin_id!r}, got {plugin_id!r})"
            )
        if plugin_type not in {"provider", "tool", "gate_plugin", "postprocessor"}:
            raise ValueError(f"{module_name}: invalid type {plugin_type!r}")
        if not isinstance(entrypoint, str) or not entrypoint:
            raise ValueError(f"{module_name}: entrypoint must be non-empty string")

        _validate_inject(inject_target, inject_key)

        # Uniqueness
        # We enforce uniqueness only for actual injection targets (tools/context overrides).
        # Multiple gate plugins may depend on the same provider key (e.g., 'gpt').
        if inject_target != "providers":
            inject_pair = (inject_target, inject_key)
            if inject_pair in seen_inject:
                raise ValueError(f"Duplicate injection key: {inject_pair!r}")
            seen_inject.add(inject_pair)

        if not determinism_required:
            raise ValueError(f"{module_name}: determinism.required must be true")

        _validate_requires_platform_api(requires_platform_api)

        # Entrypoint import validation
        _import_entrypoint_callable(entrypoint)

        manifests.append(
            PluginManifest(
                manifest_version=manifest_version,
                plugin_id=plugin_id,
                plugin_type=plugin_type,
                entrypoint=entrypoint,
                inject_target=inject_target,
                inject_key=inject_key,
                determinism_required=determinism_required,
                requires_platform_api=requires_platform_api,
            )
        )

    return manifests
