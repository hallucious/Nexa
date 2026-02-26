from __future__ import annotations

"""External plugin loading (v1).

Scope:
- Disabled by default.
- When enabled, loads python modules from a user-provided directory (default: <repo_root>/plugins).
- Each module may inject objects into runner context/providers/plugins via a simple register() hook.

External plugin contract (v1):
- File: any *.py file directly under plugins_dir OR one-level deep (plugins_dir/*/*.py).
- Must define a callable: register(*, providers: dict, plugins: dict, context: dict) -> None
- Optional:
  - PLUGIN_ID: str (defaults to filename stem)
  - REQUIRES: dict (ignored in v1, reserved for future compatibility checks)

Safety/Policy:
- No network/filesystem sandboxing in v1.
- Key conflicts are rejected (raise ValueError).
- Import errors are surfaced as ValueError with plugin path context.

This module is intentionally small; it provides only deterministic loading and conflict checks.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
import importlib.util


@dataclass(frozen=True)
class ExternalPlugin:
    plugin_id: str
    path: Path


def _iter_candidate_files(plugins_dir: Path) -> Iterable[Path]:
    # Direct children: plugins_dir/*.py
    for p in sorted(plugins_dir.glob("*.py")):
        if p.name.startswith("_"):
            continue
        yield p
    # One-level deep: plugins_dir/*/*.py (namespaces)
    for p in sorted(plugins_dir.glob("*/*.py")):
        if p.name.startswith("_"):
            continue
        yield p


def discover_external_plugins(repo_root: Path, *, plugins_dir: Path | None = None) -> List[ExternalPlugin]:
    base = plugins_dir or (repo_root / "plugins")
    if not base.exists():
        return []
    out: List[ExternalPlugin] = []
    for p in _iter_candidate_files(base):
        plugin_id = p.stem
        out.append(ExternalPlugin(plugin_id=plugin_id, path=p))
    return out


def _import_module_from_path(path: Path) -> Any:
    # Deterministic module name derived from path.
    mod_name = f"external_plugin_{path.stem}_{abs(hash(str(path.resolve())))}"
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def _guard_conflict(dst: Dict[str, Any], src: Dict[str, Any], *, plugin_id: str, target: str) -> None:
    overlap = set(dst.keys()) & set(src.keys())
    if overlap:
        keys = ", ".join(sorted(overlap))
        raise ValueError(f"External plugin '{plugin_id}' attempts to override existing {target} key(s): {keys}")


def load_external_injections(
    repo_root: Path,
    *,
    plugins_dir: Path | None = None,
    base_context: Dict[str, Any] | None = None,
    base_providers: Dict[str, Any] | None = None,
    base_plugins: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Load external plugins and return merged (context, providers, plugins).

    This function does NOT mutate the input dicts.
    """
    context: Dict[str, Any] = dict(base_context or {})
    providers: Dict[str, Any] = dict(base_providers or {})
    plugins: Dict[str, Any] = dict(base_plugins or {})

    for ep in discover_external_plugins(repo_root, plugins_dir=plugins_dir):
        try:
            mod = _import_module_from_path(ep.path)
        except Exception as e:
            raise ValueError(f"Failed to import external plugin at {ep.path}: {e}") from e

        plugin_id = getattr(mod, "PLUGIN_ID", ep.plugin_id)
        register = getattr(mod, "register", None)
        if not callable(register):
            raise ValueError(f"External plugin '{plugin_id}' at {ep.path} is missing callable register(...)")  # noqa: EM101

        # Let plugin inject into temporary dicts so we can check conflicts before merging.
        tmp_ctx: Dict[str, Any] = {}
        tmp_prov: Dict[str, Any] = {}
        tmp_plg: Dict[str, Any] = {}

        try:
            register(providers=tmp_prov, plugins=tmp_plg, context=tmp_ctx)
        except TypeError:
            # If user wrote register(providers, plugins, context) positional.
            register(tmp_prov, tmp_plg, tmp_ctx)
        except Exception as e:
            raise ValueError(f"External plugin '{plugin_id}' register() failed: {e}") from e

        _guard_conflict(context, tmp_ctx, plugin_id=plugin_id, target="context")
        _guard_conflict(providers, tmp_prov, plugin_id=plugin_id, target="providers")
        _guard_conflict(plugins, tmp_plg, plugin_id=plugin_id, target="plugins")

        context.update(tmp_ctx)
        providers.update(tmp_prov)
        plugins.update(tmp_plg)

    return context, providers, plugins
