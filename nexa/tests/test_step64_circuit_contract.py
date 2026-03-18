import json
from pathlib import Path
from src.circuit.loader import load_definition
from src.circuit.fingerprint import compute_circuit_fingerprint


def minimal_definition():
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


def test_load_definition(tmp_path: Path):
    data = minimal_definition()
    p = tmp_path / "c.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    model = load_definition(p)
    assert model.circuit_id == "c1"
    assert "n1" in model.nodes


def test_fingerprint_deterministic():
    data = minimal_definition()
    fp1 = compute_circuit_fingerprint(data)
    fp2 = compute_circuit_fingerprint(data)
    assert fp1 == fp2
