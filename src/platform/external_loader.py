from __future__ import annotations

"""src.platform.external_loader

External plugin loading utilities.

This module intentionally supports two shapes of "external plugin":

1) Step42 legacy injections
   - repo_root/plugins/*.py
   - module may define register(providers=..., plugins=..., context=...)
   - collisions are rejected

2) Step43 sandboxed callables (manifest-based)
   - plugins_dir/<plugin_id>/manifest.json
   - manifest schema used by tests:
       {
         "id": "p_ok",
         "entrypoint": "plugin:run",
         "inject": {"target": "providers", "key": "x"},
         "timeout_ms": 200,
         ...
       }
   - load_external_plugins(...) returns a mapping:
       loaded[("providers","x")] = SandboxedCallable(...)
     where SandboxedCallable has .call(**kwargs) -> (SandboxResult, value)

Notes
- We do NOT attempt full security isolation; we only provide "process + timeout" sandboxing.
- The sandbox worker returns SandboxResult(kind in {"OK","TIMEOUT","CRASH"}).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import importlib.util
import json

from src.platform.sandbox_worker import run_in_sandbox, SandboxResult


class ExternalPluginLoadError(ValueError):
    """Raised when loading external plugins fails.

    Inherits ValueError for Step42 compatibility tests.
    """


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------

def _load_module_from_path(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    if spec is None or spec.loader is None:
        raise ExternalPluginLoadError(f"Unable to import module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ExternalPluginLoadError(f"Invalid JSON manifest: {path}: {e}") from e


def _coalesce(d: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in d:
            return d[k]
    return None


def _parse_entrypoint(plugin_dir: Path, entrypoint: str) -> Tuple[Path, str]:
    # format: "plugin:run" or "plugin.py:run"
    if ":" in entrypoint:
        mod_part, fn = entrypoint.split(":", 1)
    else:
        mod_part, fn = entrypoint, "run"

    mod_part = mod_part.strip()
    fn = fn.strip() or "run"

    # Accept "plugin" meaning plugin.py
    if not mod_part.endswith(".py"):
        mod_part = mod_part + ".py"

    module_path = (plugin_dir / mod_part).resolve()
    return module_path, fn


def _parse_manifest(manifest_path: Path, data: Dict[str, Any], default_timeout_ms: int) -> Tuple[str, str, Path, str, int]:
    # Accept nested injection blocks: inject / injection
    inj = data.get("inject")
    if isinstance(inj, dict):
        data = {**data, **inj}

    inj2 = data.get("injection")
    if isinstance(inj2, dict):
        data = {**data, **inj2}

    target = _coalesce(data, ["target", "inject_to", "injection_target", "scope", "category"])
    key = _coalesce(data, ["key", "inject_key", "name"])

    if not isinstance(target, str) or target not in {"providers", "plugins", "context"}:
        raise ExternalPluginLoadError(f"manifest_missing_target: {manifest_path}")
    if not isinstance(key, str) or not key:
        raise ExternalPluginLoadError(f"manifest_missing_key: {manifest_path}")

    entrypoint = _coalesce(data, ["entrypoint", "entry_point", "callable", "function"])
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        raise ExternalPluginLoadError(f"manifest_missing_entrypoint: {manifest_path}")

    plugin_dir = manifest_path.parent
    module_path, func_name = _parse_entrypoint(plugin_dir, entrypoint.strip())
    if not module_path.exists():
        raise ExternalPluginLoadError(f"manifest_entrypoint_module_missing: {module_path}")

    timeout_ms = data.get("timeout_ms")
    if isinstance(timeout_ms, int) and timeout_ms > 0:
        tm = timeout_ms
    else:
        tm = int(default_timeout_ms)

    return target, key, module_path, func_name, tm


def _find_manifests(plugins_dir: Path) -> List[Path]:
    if not plugins_dir.exists():
        return []
    # Tests use manifest.json, but we also accept any *manifest*.json.
    out: List[Path] = []
    for p in plugins_dir.rglob("*.json"):
        name = p.name.lower()
        if name == "manifest.json" or "manifest" in name:
            out.append(p)
    return sorted(out)


# -----------------------------------------------------------------------------
# Step43: sandboxed external callables
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class SandboxedCallable:
    module_path: Path
    func_name: str
    timeout_ms: int

    def call(self, **kwargs: Any) -> Tuple[SandboxResult, Any]:
        res = run_in_sandbox(module_path=self.module_path, func_name=self.func_name, kwargs=dict(kwargs), timeout_ms=self.timeout_ms)
        return res, res.value

    # Optional convenience (not required by tests)
    def run(self, **kwargs: Any) -> Any:
        _res, val = self.call(**kwargs)
        return val


def load_external_plugins(
    *,
    plugins_dir: Path,
    enabled: bool = True,
    default_timeout_ms: int = 200,
) -> Dict[Tuple[str, str], SandboxedCallable]:
    """Load manifest-based external plugins.

    Returns mapping:
        (target, key) -> SandboxedCallable

    Raises ExternalPluginLoadError on invalid manifests, conflicts, or IO errors.
    """

    if not enabled:
        return {}

    plugins_dir = Path(plugins_dir)
    if not plugins_dir.exists():
        return {}

    loaded: Dict[Tuple[str, str], SandboxedCallable] = {}

    for manifest_path in _find_manifests(plugins_dir):
        data = _read_json(manifest_path)

        # Expected by tests: single injection manifest.
        target, key, module_path, func_name, timeout_ms = _parse_manifest(manifest_path, data, default_timeout_ms)

        tup = (target, key)
        if tup in loaded:
            raise ExternalPluginLoadError(f"Duplicate external injection: {tup}")

        loaded[tup] = SandboxedCallable(module_path=module_path, func_name=func_name, timeout_ms=timeout_ms)

    return loaded


# -----------------------------------------------------------------------------
# Step42: legacy register() loader
# -----------------------------------------------------------------------------

def load_external_injections(
    repo_root: Path,
    *,
    plugins_dir: Optional[Path] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Load legacy external injections from *.py files.

    Returns: (context, providers, plugins)

    Collision messages must include "override existing <bucket> key" for Step42 tests.
    """

    repo_root = Path(repo_root)
    if plugins_dir is None:
        plugins_dir = repo_root / "plugins"
    else:
        plugins_dir = Path(plugins_dir)

    context: Dict[str, Any] = {}
    providers: Dict[str, Any] = {}
    plugins: Dict[str, Any] = {}

    if not plugins_dir.exists():
        return context, providers, plugins

    for path in sorted(plugins_dir.glob("*.py")):
        mod = _load_module_from_path(path)
        register = getattr(mod, "register", None)
        if register is None:
            continue

        scratch_ctx: Dict[str, Any] = {}
        scratch_prov: Dict[str, Any] = {}
        scratch_plg: Dict[str, Any] = {}

        try:
            register(providers=scratch_prov, plugins=scratch_plg, context=scratch_ctx)
        except Exception as e:
            raise ExternalPluginLoadError(f"External plugin register() failed: {path}: {e}") from e

        for k in scratch_prov:
            if k in providers:
                raise ExternalPluginLoadError(f"override existing providers key: {k}")
        for k in scratch_plg:
            if k in plugins:
                raise ExternalPluginLoadError(f"override existing plugins key: {k}")
        for k in scratch_ctx:
            if k in context:
                raise ExternalPluginLoadError(f"override existing context key: {k}")

        context.update(scratch_ctx)
        providers.update(scratch_prov)
        plugins.update(scratch_plg)

    return context, providers, plugins
