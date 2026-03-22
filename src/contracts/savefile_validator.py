"""Savefile Validator - Strict validation of minimal contract.

Validates:
- Required top-level sections (meta, circuit, resources, state)
- Node IDs unique
- Entry node exists
- Edges reference valid nodes
- Resource references resolve
- Input paths are valid
- Node type/resource_ref pairing valid
"""

from __future__ import annotations

import re
from typing import List, Set

from src.contracts.savefile_format import Savefile, NodeSpec


class SavefileValidationError(Exception):
    """Raised when savefile validation fails."""
    pass


def validate_savefile(savefile: Savefile) -> List[str]:
    """Validate savefile structure.
    
    Args:
        savefile: Loaded savefile
        
    Returns:
        List of warning messages (empty if no warnings)
        
    Raises:
        SavefileValidationError: If validation fails
    """
    warnings: List[str] = []
    
    # 1. Validate meta
    if not savefile.meta.name:
        raise SavefileValidationError("meta.name must be non-empty")
    if not savefile.meta.version:
        raise SavefileValidationError("meta.version must be non-empty")
    
    # 2. Validate circuit structure
    _validate_circuit_structure(savefile)
    
    # 3. Validate resource references
    _validate_resource_references(savefile)
    
    # 4. Validate input paths
    warnings.extend(_validate_input_paths(savefile))
    
    # 5. Validate node type/resource_ref pairing
    _validate_node_types(savefile)
    
    # 6. Validate UI section (must exist but not affect execution)
    _validate_ui_section(savefile, warnings)
    
    return warnings


def _validate_ui_section(savefile: Savefile, warnings: List[str]) -> None:
    """Validate UI section exists and doesn't affect execution.
    
    UI section must exist but must not be referenced in inputs or execution logic.
    """
    # UI section existence is enforced by dataclass structure
    # Check that UI is not referenced in any input paths
    for node in savefile.circuit.nodes:
        for input_key, input_path in node.inputs.items():
            if input_path.startswith("ui."):
                raise SavefileValidationError(
                    f"Node '{node.id}' input '{input_key}' references UI section. "
                    "UI must not affect execution."
                )
    
    # This is just a structural check - ui can exist and contain any metadata
    # but it must not be used in execution


def _validate_circuit_structure(savefile: Savefile) -> None:
    """Validate circuit topology.
    
    Checks:
    - Node IDs unique
    - Entry node exists
    - Edges reference valid nodes
    """
    # Check nodes exist
    if not savefile.circuit.nodes:
        raise SavefileValidationError("circuit.nodes must not be empty")
    
    # Check node IDs unique
    node_ids = [node.id for node in savefile.circuit.nodes]
    if len(node_ids) != len(set(node_ids)):
        duplicates = [nid for nid in node_ids if node_ids.count(nid) > 1]
        raise SavefileValidationError(f"Duplicate node IDs: {set(duplicates)}")
    
    node_id_set = set(node_ids)
    
    # Check entry exists
    if savefile.circuit.entry not in node_id_set:
        raise SavefileValidationError(
            f"Entry node '{savefile.circuit.entry}' not found in nodes"
        )
    
    # Check edges reference valid nodes
    for edge in savefile.circuit.edges:
        if edge.from_node not in node_id_set:
            raise SavefileValidationError(
                f"Edge from_node '{edge.from_node}' not found in nodes"
            )
        if edge.to_node not in node_id_set:
            raise SavefileValidationError(
                f"Edge to_node '{edge.to_node}' not found in nodes"
            )


def _validate_resource_references(savefile: Savefile) -> None:
    """Validate that all resource references resolve.
    
    Checks:
    - Plugin nodes reference existing plugins
    - AI nodes reference existing prompts and providers
    """
    prompt_ids = set(savefile.resources.prompts.keys())
    provider_ids = set(savefile.resources.providers.keys())
    plugin_ids = set(savefile.resources.plugins.keys())
    
    for node in savefile.circuit.nodes:
        if node.type == "plugin":
            plugin_ref = node.resource_ref.get("plugin")
            if not plugin_ref:
                raise SavefileValidationError(
                    f"Plugin node '{node.id}' missing 'plugin' in resource_ref"
                )
            if plugin_ref not in plugin_ids:
                raise SavefileValidationError(
                    f"Plugin node '{node.id}' references unknown plugin '{plugin_ref}'"
                )
        
        elif node.type == "ai":
            prompt_ref = node.resource_ref.get("prompt")
            provider_ref = node.resource_ref.get("provider")
            
            if not prompt_ref:
                raise SavefileValidationError(
                    f"AI node '{node.id}' missing 'prompt' in resource_ref"
                )
            if not provider_ref:
                raise SavefileValidationError(
                    f"AI node '{node.id}' missing 'provider' in resource_ref"
                )
            
            if prompt_ref not in prompt_ids:
                raise SavefileValidationError(
                    f"AI node '{node.id}' references unknown prompt '{prompt_ref}'"
                )
            if provider_ref not in provider_ids:
                raise SavefileValidationError(
                    f"AI node '{node.id}' references unknown provider '{provider_ref}'"
                )


def _validate_input_paths(savefile: Savefile) -> List[str]:
    """Validate input reference paths are structurally valid.
    
    Returns:
        List of warnings (empty if all valid)
    """
    warnings: List[str] = []
    node_ids = {node.id for node in savefile.circuit.nodes}
    
    # Allowed path patterns
    state_pattern = re.compile(r'^state\.(input|working|memory)\..+$')
    node_pattern = re.compile(r'^node\.[a-zA-Z0-9_-]+\..+$')
    
    for node in savefile.circuit.nodes:
        for input_key, input_path in node.inputs.items():
            # Check if path matches allowed patterns
            if not (state_pattern.match(input_path) or node_pattern.match(input_path)):
                warnings.append(
                    f"Node '{node.id}' input '{input_key}' has invalid path: '{input_path}'"
                )
                continue
            
            # If node reference, check node exists
            if input_path.startswith("node."):
                parts = input_path.split(".", 2)
                if len(parts) >= 2:
                    referenced_node = parts[1]
                    if referenced_node not in node_ids:
                        warnings.append(
                            f"Node '{node.id}' references non-existent node '{referenced_node}'"
                        )
    
    return warnings


def _validate_node_types(savefile: Savefile) -> None:
    """Validate node type matches resource_ref structure.
    
    Checks:
    - plugin nodes have exactly resource_ref.plugin
    - ai nodes have exactly resource_ref.prompt + resource_ref.provider
    """
    for node in savefile.circuit.nodes:
        if node.type not in ("plugin", "ai"):
            raise SavefileValidationError(
                f"Node '{node.id}' has invalid type: '{node.type}' (must be 'plugin' or 'ai')"
            )
        
        if node.type == "plugin":
            if "plugin" not in node.resource_ref:
                raise SavefileValidationError(
                    f"Plugin node '{node.id}' must have 'plugin' in resource_ref"
                )
            # Plugin nodes should not have prompt/provider refs
            if "prompt" in node.resource_ref or "provider" in node.resource_ref:
                raise SavefileValidationError(
                    f"Plugin node '{node.id}' should not have prompt/provider in resource_ref"
                )
        
        elif node.type == "ai":
            if "prompt" not in node.resource_ref or "provider" not in node.resource_ref:
                raise SavefileValidationError(
                    f"AI node '{node.id}' must have both 'prompt' and 'provider' in resource_ref"
                )
            # AI nodes should not have plugin ref
            if "plugin" in node.resource_ref:
                raise SavefileValidationError(
                    f"AI node '{node.id}' should not have 'plugin' in resource_ref"
                )
