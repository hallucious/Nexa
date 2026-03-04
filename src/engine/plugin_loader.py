
from importlib import import_module
from typing import List

from src.platform.plugin_registry import registry


def load_plugins(plugin_ids: List[str]):
    """Resolve plugin IDs using platform registry and return plugin instances."""
    reg = registry()
    plugins = []

    for pid in plugin_ids:
        if pid not in reg:
            raise ValueError(f"Unknown plugin id: {pid}")

        contract = reg[pid]
        module = import_module(contract.module)

        # resolve entrypoint symbol
        for sym in contract.required_symbols:
            if hasattr(module, sym):
                obj = getattr(module, sym)

                # allow factory or class
                if callable(obj):
                    try:
                        plugin = obj()
                    except TypeError:
                        plugin = obj
                    plugins.append(plugin)
                    break
        else:
            raise RuntimeError(f"No entrypoint symbol found for plugin {pid}")

    return plugins
