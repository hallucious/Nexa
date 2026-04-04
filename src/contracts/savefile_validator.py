"""Savefile Validator - Strict validation of canonical savefile contract.

Validates:
- Required top-level sections are present in the loaded savefile object
- UI section exists but remains execution-independent (legacy canonical path)
- Node IDs unique
- Entry node exists
- Edges reference valid nodes
- Resource references resolve
- Input paths are valid
- Node type/resource_ref pairing valid
- SubcircuitNode structural validity
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from src.contracts.savefile_format import Savefile, NodeSpec


class SavefileValidationError(Exception):
    """Raised when savefile validation fails."""


def validate_savefile(savefile: Savefile) -> List[str]:
    warnings: List[str] = []

    if not savefile.meta.name:
        raise SavefileValidationError("meta.name must be non-empty")
    if not savefile.meta.version:
        raise SavefileValidationError("meta.version must be non-empty")

    _validate_ui_section(savefile)
    _validate_circuit_structure(savefile)
    _validate_resource_references(savefile)
    _validate_input_paths(savefile)
    _validate_node_types(savefile)
    _validate_subcircuit_nodes(savefile)

    return warnings


def _validate_ui_section(savefile: Savefile) -> None:
    if savefile.ui is None:
        # Keep legacy validator behavior unchanged for existing canonical savefile tests.
        raise SavefileValidationError("ui section must exist")


def _validate_circuit_structure(savefile: Savefile) -> None:
    node_ids = [node.id for node in savefile.circuit.nodes]
    if len(node_ids) != len(set(node_ids)):
        raise SavefileValidationError("Duplicate node id detected")

    node_id_set = set(node_ids)
    if savefile.circuit.entry not in node_id_set:
        raise SavefileValidationError(f"Entry node '{savefile.circuit.entry}' not found in nodes")

    for edge in savefile.circuit.edges:
        if edge.from_node not in node_id_set:
            raise SavefileValidationError(f"Edge source '{edge.from_node}' not found in nodes")
        if edge.to_node not in node_id_set:
            raise SavefileValidationError(f"Edge target '{edge.to_node}' not found in nodes")


def _validate_resource_references(savefile: Savefile) -> None:
    for node in savefile.circuit.nodes:
        node_kind = node.node_kind
        if node_kind == "plugin":
            plugin_ref = node.resource_ref.get("plugin")
            if not plugin_ref:
                raise SavefileValidationError(f"Plugin node '{node.id}' missing resource_ref.plugin")
            if plugin_ref not in savefile.resources.plugins:
                raise SavefileValidationError(f"Plugin node '{node.id}' references unknown plugin '{plugin_ref}'")
        elif node_kind == "ai":
            prompt_ref = node.resource_ref.get("prompt")
            provider_ref = node.resource_ref.get("provider")
            if not prompt_ref or not provider_ref:
                raise SavefileValidationError(
                    f"AI node '{node.id}' requires resource_ref.prompt and resource_ref.provider"
                )
            if prompt_ref not in savefile.resources.prompts:
                raise SavefileValidationError(f"AI node '{node.id}' references unknown prompt '{prompt_ref}'")
            if provider_ref not in savefile.resources.providers:
                raise SavefileValidationError(f"AI node '{node.id}' references unknown provider '{provider_ref}'")
        elif node_kind == "subcircuit":
            # resolved later
            continue
        else:
            raise SavefileValidationError(f"Unknown node type/kind '{node_kind}' for node '{node.id}'")


def _validate_input_paths(savefile: Savefile) -> None:
    node_id_set = {node.id for node in savefile.circuit.nodes}
    for node in savefile.circuit.nodes:
        for key, path in node.inputs.items():
            if not isinstance(path, str) or not path:
                raise SavefileValidationError(f"Node '{node.id}' input '{key}' path must be non-empty string")
            if path.startswith("ui."):
                raise SavefileValidationError(f"Node '{node.id}' input '{key}' references UI section. UI must not affect execution.")
            if path.startswith(("state.input.", "state.working.", "state.memory.", "input.")):
                continue
            if path.startswith("node."):
                parts = path.split(".")
                if len(parts) < 3:
                    raise SavefileValidationError(f"Node '{node.id}' input '{key}' has invalid node path '{path}'")
                ref_node_id = parts[1]
                if ref_node_id not in node_id_set:
                    raise SavefileValidationError(f"Node '{node.id}' input '{key}' references unknown node '{ref_node_id}'")
                continue
            raise SavefileValidationError(f"Node '{node.id}' input '{key}' has unsupported path '{path}'")


def _validate_node_types(savefile: Savefile) -> None:
    for node in savefile.circuit.nodes:
        node_kind = node.node_kind
        if node_kind == "plugin":
            if "plugin" not in node.resource_ref:
                raise SavefileValidationError(f"Plugin node '{node.id}' missing resource_ref.plugin")
        elif node_kind == "ai":
            if "prompt" not in node.resource_ref or "provider" not in node.resource_ref:
                raise SavefileValidationError(f"AI node '{node.id}' must declare prompt and provider resource refs")
        elif node_kind == "subcircuit":
            sub = node.execution.get("subcircuit")
            if not isinstance(sub, dict):
                raise SavefileValidationError(f"Subcircuit node '{node.id}' missing execution.subcircuit block")
            if not isinstance(sub.get("child_circuit_ref"), str) or not sub.get("child_circuit_ref"):
                raise SavefileValidationError(f"Subcircuit node '{node.id}' missing child_circuit_ref")
            if not isinstance(sub.get("input_mapping"), dict):
                raise SavefileValidationError(f"Subcircuit node '{node.id}' input_mapping must be an object")
            if not isinstance(sub.get("output_binding"), dict):
                raise SavefileValidationError(f"Subcircuit node '{node.id}' output_binding must be an object")
        else:
            raise SavefileValidationError(f"Unknown node type/kind '{node_kind}' for node '{node.id}'")


def _resolve_child_circuit_ref(savefile: Savefile, child_ref: str) -> Dict[str, Any]:
    if child_ref.startswith("internal:"):
        name = child_ref.split(":", 1)[1]
        child = savefile.circuit.subcircuits.get(name)
        if child is None:
            raise SavefileValidationError(f"Subcircuit child ref '{child_ref}' not found in local subcircuits registry")
        if not isinstance(child, dict):
            raise SavefileValidationError(f"Subcircuit child ref '{child_ref}' must resolve to an object")
        return child
    raise SavefileValidationError(f"Unsupported child_circuit_ref '{child_ref}'")


def _child_output_names(child: Dict[str, Any]) -> Set[str]:
    names: Set[str] = set()
    for item in child.get("outputs", []):
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.add(item["name"])
    return names


def _validate_subcircuit_recursion(savefile: Savefile) -> None:
    graph: Dict[str, Set[str]] = {}
    for name, child in savefile.circuit.subcircuits.items():
        refs: Set[str] = set()
        for node in child.get("nodes", []):
            if not isinstance(node, dict):
                continue
            if (node.get("kind") or node.get("type")) != "subcircuit":
                continue
            sub = node.get("execution", {}).get("subcircuit", {})
            child_ref = sub.get("child_circuit_ref")
            if isinstance(child_ref, str) and child_ref.startswith("internal:"):
                refs.add(child_ref.split(":", 1)[1])
        graph[name] = refs

    visiting: Set[str] = set()
    visited: Set[str] = set()

    def dfs(name: str, depth: int) -> None:
        if depth > 2:
            raise SavefileValidationError("Subcircuit max depth exceeded")
        if name in visiting:
            raise SavefileValidationError("Subcircuit recursive reference detected")
        if name in visited:
            return
        visiting.add(name)
        for nxt in graph.get(name, set()):
            dfs(nxt, depth + 1)
        visiting.remove(name)
        visited.add(name)

    for name in graph:
        dfs(name, 0)


def _validate_subcircuit_nodes(savefile: Savefile) -> None:
    _validate_subcircuit_recursion(savefile)
    for node in savefile.circuit.nodes:
        if node.node_kind != "subcircuit":
            continue
        sub = node.execution["subcircuit"]
        child_ref = sub["child_circuit_ref"]
        child = _resolve_child_circuit_ref(savefile, child_ref)
        child_nodes = child.get("nodes", [])
        if not isinstance(child_nodes, list) or not child_nodes:
            raise SavefileValidationError(f"Subcircuit node '{node.id}' child circuit '{child_ref}' must declare at least one node")
        child_outputs = _child_output_names(child)
        if not child_outputs:
            raise SavefileValidationError(f"Subcircuit node '{node.id}' child circuit '{child_ref}' must declare outputs")
        output_binding = sub.get("output_binding", {})
        for parent_key, target in output_binding.items():
            if not isinstance(target, str) or not target.startswith("child.output."):
                raise SavefileValidationError(f"Subcircuit node '{node.id}' output_binding '{parent_key}' must target child.output.*")
            child_name = target[len("child.output."):]
            if child_name not in child_outputs:
                raise SavefileValidationError(
                    f"Subcircuit node '{node.id}' references missing child output '{child_name}'"
                )
        input_mapping = sub.get("input_mapping", {})
        if not input_mapping:
            raise SavefileValidationError(f"Subcircuit node '{node.id}' must declare at least one input_mapping entry")
        for key, path in input_mapping.items():
            if not isinstance(path, str) or not path:
                raise SavefileValidationError(f"Subcircuit node '{node.id}' input_mapping '{key}' must be non-empty string")
            if path.startswith(("state.input.", "state.working.", "state.memory.", "input.")):
                continue
            if path.startswith("node."):
                continue
            raise SavefileValidationError(f"Subcircuit node '{node.id}' has unsupported input_mapping path '{path}'")
