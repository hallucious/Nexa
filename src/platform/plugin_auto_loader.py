from __future__ import annotations

import importlib
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict

from src.platform.plugin_definition import PluginDefinition


class PluginAutoLoaderError(ValueError):
    """Raised when plugin auto-loading fails."""


def _load_module_from_file(file_path: Path) -> ModuleType:
    spec = spec_from_file_location(f"nexa_plugin_{file_path.stem}", file_path)
    if spec is None or spec.loader is None:
        raise PluginAutoLoaderError(
            f"failed to create import spec for plugin file: {file_path}"
        )

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_plugins_from_module(module: ModuleType, file_path: Path) -> Dict[str, Any]:
    if hasattr(module, "PLUGINS"):
        plugins = getattr(module, "PLUGINS")
        if not isinstance(plugins, dict):
            raise PluginAutoLoaderError(
                f"PLUGINS must be dict[str, callable] in {file_path}"
            )
        return plugins

    if hasattr(module, "register_plugins"):
        plugins = module.register_plugins()
        if not isinstance(plugins, dict):
            raise PluginAutoLoaderError(
                f"register_plugins() must return dict[str, callable] in {file_path}"
            )
        return plugins

    raise PluginAutoLoaderError(
        f"plugin file must define PLUGINS or register_plugins(): {file_path}"
    )


def _validate_plugin(plugin_id: str, plugin_payload: Any, file_path: Path) -> PluginDefinition:
    if not isinstance(plugin_id, str) or not plugin_id.strip():
        raise PluginAutoLoaderError(
            f"plugin id must be non-empty string in {file_path}"
        )

    if callable(plugin_payload):
        return PluginDefinition(
            plugin_id=plugin_id,
            version="1.0.0",
            description="",
            callable=plugin_payload,
        )

    if not isinstance(plugin_payload, dict):
        raise PluginAutoLoaderError(
            f"plugin definition must be callable or dict in {file_path}"
        )

    fn = plugin_payload.get("callable")
    if not callable(fn):
        raise PluginAutoLoaderError(
            f"plugin callable missing or invalid: {plugin_id} in {file_path}"
        )

    version = plugin_payload.get("version", "1.0.0")
    description = plugin_payload.get("description", "")

    if not isinstance(version, str):
        raise PluginAutoLoaderError(
            f"plugin version must be string: {plugin_id}"
        )

    if not isinstance(description, str):
        raise PluginAutoLoaderError(
            f"plugin description must be string: {plugin_id}"
        )

    return PluginDefinition(
        plugin_id=plugin_id,
        version=version,
        description=description,
        callable=fn,
    )



_ENTRY_CACHE: Dict[str, Callable[..., Any]] = {}


def load_plugin_entry(entry: str) -> Callable[..., Any]:
    """Load a plugin callable from a module.function entry path.

    This is the runtime bridge loader for savefile/plugin-entry style plugin references.
    It is intentionally separate from versioned registry resolution.
    """
    if entry in _ENTRY_CACHE:
        return _ENTRY_CACHE[entry]

    parts = entry.rsplit(".", 1)
    if len(parts) != 2:
        raise PluginAutoLoaderError(f"invalid plugin entry path: {entry}")

    module_name, function_name = parts
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise PluginAutoLoaderError(f"cannot import plugin module '{module_name}': {e}") from e

    if not hasattr(module, function_name):
        raise PluginAutoLoaderError(
            f"plugin module '{module_name}' has no callable '{function_name}'"
        )

    plugin_callable = getattr(module, function_name)
    if not callable(plugin_callable):
        raise PluginAutoLoaderError(
            f"plugin entry is not callable: {entry}"
        )

    _ENTRY_CACHE[entry] = plugin_callable
    return plugin_callable

def load_plugin_registry(plugin_dir: str) -> Dict[str, PluginDefinition]:
    """
    Load plugins from a directory.

    Supported file contract:
    1. PLUGINS = {"plugin_id": callable}
    2. PLUGINS = {"plugin_id": {"callable": fn, "version": "...", "description": "..."}}
    3. def register_plugins() -> same dict shape as above
    """
    path = Path(plugin_dir)

    if not path.exists():
        return {}

    if not path.is_dir():
        raise PluginAutoLoaderError(f"plugin path is not a directory: {plugin_dir}")

    registry: Dict[str, PluginDefinition] = {}

    for file_path in sorted(path.glob("*.py")):
        if file_path.name.startswith("_"):
            continue

        module = _load_module_from_file(file_path)
        plugins = _extract_plugins_from_module(module, file_path)

        for plugin_id, plugin_payload in plugins.items():
            plugin = _validate_plugin(plugin_id, plugin_payload, file_path)

            if plugin.plugin_id in registry:
                raise PluginAutoLoaderError(
                    f"duplicate plugin id detected: {plugin.plugin_id}"
                )

            registry[plugin.plugin_id] = plugin

    return registry