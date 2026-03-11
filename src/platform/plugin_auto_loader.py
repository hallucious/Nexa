from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any, Dict


class PluginAutoLoaderError(ValueError):
    """Raised when plugin auto-loading fails."""


def _load_module_from_file(file_path: Path) -> ModuleType:
    spec = spec_from_file_location(f"nexa_plugin_{file_path.stem}", file_path)
    if spec is None or spec.loader is None:
        raise PluginAutoLoaderError(f"failed to create import spec for plugin file: {file_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_plugins_from_module(module: ModuleType, file_path: Path) -> Dict[str, Any]:
    if hasattr(module, "PLUGINS"):
        plugins = getattr(module, "PLUGINS")
        if not isinstance(plugins, dict):
            raise PluginAutoLoaderError(f"PLUGINS must be dict[str, callable] in {file_path}")
        return plugins

    if hasattr(module, "register_plugins"):
        plugins = module.register_plugins()
        if not isinstance(plugins, dict):
            raise PluginAutoLoaderError(f"register_plugins() must return dict[str, callable] in {file_path}")
        return plugins

    raise PluginAutoLoaderError(
        f"plugin file must define PLUGINS or register_plugins(): {file_path}"
    )


def load_plugin_registry(plugin_dir: str) -> Dict[str, Any]:
    """
    Load plugin callables from a directory.

    Supported file contract:
    1. PLUGINS = {"plugin_id": callable}
    2. def register_plugins() -> {"plugin_id": callable}
    """
    path = Path(plugin_dir)

    if not path.exists():
        return {}

    if not path.is_dir():
        raise PluginAutoLoaderError(f"plugin path is not a directory: {plugin_dir}")

    registry: Dict[str, Any] = {}

    for file_path in sorted(path.glob("*.py")):
        if file_path.name.startswith("_"):
            continue

        module = _load_module_from_file(file_path)
        plugins = _extract_plugins_from_module(module, file_path)

        for plugin_id, plugin_callable in plugins.items():
            if not isinstance(plugin_id, str) or not plugin_id:
                raise PluginAutoLoaderError(f"plugin id must be non-empty string in {file_path}")
            if not callable(plugin_callable):
                raise PluginAutoLoaderError(f"plugin must be callable: {plugin_id} in {file_path}")
            if plugin_id in registry:
                raise PluginAutoLoaderError(f"duplicate plugin id detected: {plugin_id}")
            registry[plugin_id] = plugin_callable

    return registry