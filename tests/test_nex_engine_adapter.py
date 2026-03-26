from __future__ import annotations

from src.engine.cli_legacy_nex_runtime import build_engine_from_nex, deserialize_nex
from src.engine.types import NodeStatus


def _example_nex_dict():
    return {
        "format": {"kind": "nexa.circuit", "version": "1.0.0"},
        "circuit": {
            "circuit_id": "demo.story_pipeline",
            "name": "Story Pipeline Demo",
            "entry_node_id": "n1",
            "description": "Minimal example Nex circuit for adapter testing",
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
        "edges": [{"edge_id": "e1", "src_node_id": "n1", "dst_node_id": "n2"}],
        "flow": [{"rule_id": "f1", "node_id": "n2", "policy": "ALL_SUCCESS"}],
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


def test_engine_built_from_nex_executes_minimally():
    raw = _example_nex_dict()
    circuit = deserialize_nex(raw)

    engine = build_engine_from_nex(circuit)
    trace = engine.execute(revision_id="r1")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n2"].node_status == NodeStatus.SUCCESS


def test_build_engine_from_nex_preserves_execution_policies_in_engine():
    raw = _example_nex_dict()
    circuit = deserialize_nex(raw)

    engine = build_engine_from_nex(circuit)

    assert engine.node_failure_policies["n2"].value == "STRICT"
    assert engine.node_fallback_map["n1"] == "n1_backup"
    assert engine.node_retry_policy["n1"].max_attempts == 2


def test_build_engine_from_nex_preserves_legacy_metadata_for_execution():
    raw = _example_nex_dict()
    circuit = deserialize_nex(raw)

    engine = build_engine_from_nex(circuit)
    adapter_meta = engine.meta["_nex_adapter"]

    assert adapter_meta["format"]["kind"] == "nexa.circuit"
    assert adapter_meta["circuit"]["circuit_id"] == "demo.story_pipeline"
    assert adapter_meta["node_specs"]["n1"]["prompt_ref"] == "prompt.main"
    assert adapter_meta["plugins"][0]["plugin_id"] == "text.cleaner"
