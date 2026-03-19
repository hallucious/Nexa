from __future__ import annotations

from typing import List

from src.contracts.nex_format import NexCircuit


class NexValidationError(Exception):
    pass


def validate_nex(circuit: NexCircuit) -> List[str]:
    """Validate NexCircuit structure. Returns list of warnings."""
    warnings: List[str] = []

    # 1. format validation
    if circuit.format.kind != "nexa.circuit":
        raise NexValidationError("Invalid format.kind")

    if circuit.format.version != "1.0.0":
        warnings.append("Unknown format version")

    # 2. entry node exists
    node_ids = {node.node_id for node in circuit.nodes}
    if circuit.circuit.entry_node_id not in node_ids:
        raise NexValidationError("entry_node_id not found in nodes")

    # 3. edge validation
    for edge in circuit.edges:
        if edge.src_node_id not in node_ids:
            raise NexValidationError(f"Edge src not found: {edge.src_node_id}")
        if edge.dst_node_id not in node_ids:
            raise NexValidationError(f"Edge dst not found: {edge.dst_node_id}")

    # 4. retry policy validation
    for node_id, retry in circuit.execution.node_retry_policy.items():
        if retry.max_attempts < 1:
            raise NexValidationError(f"Invalid retry config for {node_id}")

    # 5. plugin validation (basic)
    plugin_ids = {p.plugin_id for p in circuit.plugins}
    for node in circuit.nodes:
        for ref in node.plugin_refs:
            if ref not in plugin_ids:
                warnings.append(f"Plugin not declared: {ref}")

    return warnings
