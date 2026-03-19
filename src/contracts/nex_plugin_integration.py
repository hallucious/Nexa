# SAFE INTEGRATION LAYER (DO NOT REPLACE EXISTING ADAPTER)

from pathlib import Path
from src.contracts.nex_plugin_resolver import resolve_plugins


def validate_plugins_from_nex(nex_data: dict, bundle_path: str):
    plugin_refs = nex_data.get("plugin_refs", [])
    plugins_dir = Path(bundle_path) / "plugins"

    result = resolve_plugins(plugin_refs, plugins_dir)

    if result.missing_required:
        raise RuntimeError(f"Missing required plugins: {result.missing_required}")

    return result
