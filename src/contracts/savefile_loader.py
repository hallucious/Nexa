"""Savefile Loader - Loads canonical executable savefile contract.

Loads .nex files in savefile v2.0 format with required root sections:
- meta
- circuit
- resources
- state
- ui
"""

from __future__ import annotations

import json
from typing import Any, Dict

from src.contracts.savefile_format import (
    CircuitSpec,
    EdgeSpec,
    NodeSpec,
    PluginResource,
    PromptResource,
    ProviderResource,
    ResourcesSpec,
    Savefile,
    SavefileMeta,
    StateSpec,
    UISpec,
)


def _load_meta(raw: Dict[str, Any]) -> SavefileMeta:
    """Load meta section."""
    return SavefileMeta(
        name=raw["name"],
        version=raw["version"],
        description=raw.get("description"),
    )


def _load_circuit(raw: Dict[str, Any]) -> CircuitSpec:
    """Load circuit section with nodes and edges."""
    nodes = [
        NodeSpec(
            id=n["id"],
            type=n["type"],
            resource_ref=dict(n.get("resource_ref", {})),
            inputs=dict(n.get("inputs", {})),
            outputs=dict(n.get("outputs", {})),
        )
        for n in raw.get("nodes", [])
    ]
    
    edges = [
        EdgeSpec(
            from_node=e.get("from") or e.get("from_node"),
            to_node=e.get("to") or e.get("to_node"),
        )
        for e in raw.get("edges", [])
    ]
    
    return CircuitSpec(
        entry=raw["entry"],
        nodes=nodes,
        edges=edges,
    )


def _load_resources(raw: Dict[str, Any]) -> ResourcesSpec:
    """Load resources section."""
    prompts = {
        key: PromptResource(template=val["template"])
        for key, val in raw.get("prompts", {}).items()
    }
    
    providers = {
        key: ProviderResource(
            type=val["type"],
            model=val["model"],
            config=val.get("config", {}),
        )
        for key, val in raw.get("providers", {}).items()
    }
    
    plugins = {
        key: PluginResource(entry=val["entry"])
        for key, val in raw.get("plugins", {}).items()
    }
    
    return ResourcesSpec(
        prompts=prompts,
        providers=providers,
        plugins=plugins,
    )


def _load_state(raw: Dict[str, Any]) -> StateSpec:
    """Load state section."""
    return StateSpec(
        input=raw.get("input", {}),
        working=raw.get("working", {}),
        memory=raw.get("memory", {}),
    )


def _load_ui(raw: Dict[str, Any]) -> UISpec:
    """Load UI section (execution-independent)."""
    return UISpec(
        layout=raw.get("layout", {}),
        metadata=raw.get("metadata", {}),
    )


def load_savefile(data: Dict[str, Any]) -> Savefile:
    """Load savefile from dict.
    
    Args:
        data: Raw JSON data
        
    Returns:
        Savefile instance
        
    Raises:
        KeyError: If any required root section is missing
    """
    required_sections = ("meta", "circuit", "resources", "state", "ui")
    missing = [section for section in required_sections if section not in data]
    if missing:
        raise KeyError(
            "Missing required savefile section(s): " + ", ".join(missing)
        )

    return Savefile(
        meta=_load_meta(data["meta"]),
        circuit=_load_circuit(data["circuit"]),
        resources=_load_resources(data["resources"]),
        state=_load_state(data["state"]),
        ui=_load_ui(data["ui"]),
    )


def load_savefile_from_path(path: str) -> Savefile:
    """Load savefile from JSON file path.
    
    Args:
        path: Path to .nex file
        
    Returns:
        Savefile instance
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return load_savefile(data)
