import pytest
from src.circuit.validator import validate_circuit


def minimal():
    return {
        "schema": "hyper-ai.definition_language",
        "schema_version": "1.0.0",
        "circuit_id": "c1",
        "title": "t",
        "nodes": [
            {"id": "n1", "kind": "ai_task", "name": "A"},
            {"id": "n2", "kind": "ai_task", "name": "B"},
        ],
        "edges": [
            {"from": "n1", "to": "n2", "kind": "next"}
        ],
        "entry_node_id": "n1",
        "exit_policy": {"mode": "first_terminal"},
    }


def test_cycle_detection():
    d = minimal()
    d["edges"].append({"from": "n2", "to": "n1", "kind": "next"})
    with pytest.raises(ValueError):
        validate_circuit(d)


def test_unreachable():
    d = minimal()
    d["nodes"].append({"id": "n3", "kind": "ai_task", "name": "C"})
    with pytest.raises(ValueError):
        validate_circuit(d)


def test_unknown_field():
    d = minimal()
    d["unknown"] = 1
    with pytest.raises(ValueError):
        validate_circuit(d)
