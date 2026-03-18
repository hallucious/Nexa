"""
feature_registry.py

Registry of known Nexa features.
Each feature entry provides metadata used by the step generator.
"""
from __future__ import annotations

from typing import Dict, Any

FEATURES: Dict[str, Dict[str, Any]] = {
    "execution_diff": {
        "layer": "engine",
        "goal": "Compare two execution runs and surface differences",
        "steps": [
            "Execution Diff Data Model",
            "Execution Diff Engine",
            "Execution Diff CLI",
            "Execution Diff Formatter",
            "Execution Diff Tests",
        ],
    },
    "context_key_schema": {
        "layer": "contracts",
        "goal": "Lock Working Context key schema at contract level",
        "steps": [
            "Context Key Schema Contract",
            "Context Key Validator",
            "Context Key Tests",
        ],
    },
    "execution_trace": {
        "layer": "engine",
        "goal": "Record and expose full execution trace per run",
        "steps": [
            "Trace Model",
            "Trace Recorder",
            "Trace CLI",
            "Trace Tests",
        ],
    },
    "plugin_system": {
        "layer": "platform",
        "goal": "Enable plugin registration and execution within nodes",
        "steps": [
            "Plugin Contract",
            "Plugin Registry",
            "Plugin Executor",
            "Plugin CLI",
            "Plugin Tests",
        ],
    },
}


def list_features() -> list[str]:
    """Return all registered feature names."""
    return sorted(FEATURES.keys())


def get_feature(name: str) -> Dict[str, Any]:
    """Return feature metadata. Raises KeyError if unknown."""
    if name not in FEATURES:
        raise KeyError(f"Unknown feature: {name!r}. Available: {list_features()}")
    return FEATURES[name]
