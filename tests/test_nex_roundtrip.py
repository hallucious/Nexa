from __future__ import annotations

from src.contracts.nex_loader import deserialize_nex, load_nex_file
from src.contracts.nex_serializer import save_nex_file, serialize_nex
from src.contracts.nex_validator import validate_nex


def _example_nex_dict():
    return {
        "format": {"kind": "nexa.circuit", "version": "1.0.0"},
        "circuit": {
            "circuit_id": "demo.story_pipeline",
            "name": "Story Pipeline Demo",
            "entry_node_id": "n1",
            "description": "Minimal example Nex circuit for round-trip testing",
        },
        "nodes": [
            {
                "node_id": "n1",
                "kind": "execution",
                "prompt_ref": "prompt.main",
                "provider_ref": "provider.openai.gpt5",
                "plugin_refs": ["text.cleaner"],
            },
            {
                "node_id": "n2",
                "kind": "execution",
                "prompt_ref": "prompt.summary",
                "provider_ref": "provider.openai.gpt5",
                "plugin_refs": [],
            },
        ],
        "edges": [
            {"edge_id": "e1", "src_node_id": "n1", "dst_node_id": "n2"},
        ],
        "flow": [
            {"rule_id": "f1", "node_id": "n2", "policy": "ALL_SUCCESS"},
        ],
        "execution": {
            "strict_determinism": False,
            "node_failure_policies": {"n2": "STRICT"},
            "node_fallback_map": {"n1": "n1_backup"},
            "node_retry_policy": {"n1": {"max_attempts": 2}},
        },
        "resources": {
            "prompts": {
                "prompt.main": {"template": "Summarize: {{input.text}}"},
                "prompt.summary": {"template": "Create summary from {{n1.output}}"},
            },
            "providers": {
                "provider.openai.gpt5": {
                    "provider_type": "openai",
                    "model": "gpt-5",
                    "config": {},
                }
            },
        },
        "plugins": [
            {"plugin_id": "text.cleaner", "version": "1.0.0", "required": True},
        ],
    }


def test_deserialize_validate_roundtrip(tmp_path):
    raw = _example_nex_dict()

    circuit = deserialize_nex(raw)
    warnings = validate_nex(circuit)
    assert warnings == []

    out_path = tmp_path / "example.nex"
    save_nex_file(circuit, str(out_path))

    loaded = load_nex_file(str(out_path))

    assert loaded.format.kind == "nexa.circuit"
    assert loaded.format.version == "1.0.0"
    assert loaded.circuit.entry_node_id == "n1"
    assert [n.node_id for n in loaded.nodes] == ["n1", "n2"]
    assert loaded.execution.node_retry_policy["n1"].max_attempts == 2
    assert loaded.execution.node_fallback_map["n1"] == "n1_backup"
    assert loaded.plugins[0].plugin_id == "text.cleaner"

    original_dict = serialize_nex(circuit)
    loaded_dict = serialize_nex(loaded)
    assert original_dict == loaded_dict


def test_example_nex_file_shape():
    raw = _example_nex_dict()

    circuit = deserialize_nex(raw)
    warnings = validate_nex(circuit)

    assert warnings == []
    assert circuit.circuit.circuit_id == "demo.story_pipeline"
    assert circuit.resources.prompts["prompt.main"].template.startswith("Summarize")


def test_save_nex_file_requires_nex_extension(tmp_path):
    raw = _example_nex_dict()
    circuit = deserialize_nex(raw)

    bad_path = tmp_path / "example.json"

    import pytest

    with pytest.raises(ValueError, match=r"legacy NexCircuit files must use \.nex extension"):
        save_nex_file(circuit, str(bad_path))
