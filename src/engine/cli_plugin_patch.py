# PATCH: CLI plugin bundle support (non-destructive)

from src.contracts.nex_plugin_integration import validate_plugins_from_nex

def run_with_plugin_validation(nex_data: dict, bundle_path: str):
    if bundle_path:
        validate_plugins_from_nex(nex_data, bundle_path)
