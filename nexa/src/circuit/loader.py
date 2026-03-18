import json
from pathlib import Path
from typing import Dict, Any
from .model import CircuitModel, NodeModel, EdgeModel
from .validator import validate_circuit


SUPPORTED_SCHEMA = "hyper-ai.definition_language"
SUPPORTED_VERSION = "1.0.0"


def load_definition(path: Path) -> CircuitModel:
    data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    if data.get("schema") != SUPPORTED_SCHEMA:
        raise ValueError("Invalid schema")

    if data.get("schema_version") != SUPPORTED_VERSION:
        raise ValueError("Unsupported schema_version")

    validate_circuit(data)

    nodes = {n["id"]: NodeModel(id=n["id"], raw=n) for n in data["nodes"]}

    edges = [
        EdgeModel(
            from_id=e["from"],
            to_id=e["to"],
            kind=e["kind"],
            raw=e,
        )
        for e in data["edges"]
    ]

    return CircuitModel(
        circuit_id=data["circuit_id"],
        nodes=nodes,
        edges=edges,
        entry_node_id=data["entry_node_id"],
        raw=data,
    )
