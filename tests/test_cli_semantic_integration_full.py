from __future__ import annotations

import json

from src.engine.cli import _render_policy_output, main
from src.engine.execution_regression_policy import PolicyDecision


def _example_nex_dict():
    return {
        "format": {"kind": "nexa.circuit", "version": "1.0.0"},
        "circuit": {
            "circuit_id": "demo.story_pipeline",
            "name": "Story Pipeline Demo",
            "entry_node_id": "n1",
            "description": "Minimal example Nex circuit for engine CLI tests",
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
            "node_fallback_map": {},
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


def test_render_policy_output_includes_status_and_reasons():
    decision = PolicyDecision(status="FAIL", reasons=["FAIL: critical regression detected"])
    output = _render_policy_output(decision)
    assert output == "Status: FAIL\nFAIL: critical regression detected"


def test_cli_policy_payload_contains_display_field(tmp_path):
    circuit_path = tmp_path / "example.nex"
    circuit_path.write_text(json.dumps(_example_nex_dict(), indent=2), encoding="utf-8")

    baseline_payload = {
        "circuit_id": "demo.story_pipeline",
        "status": "SUCCESS",
        "nodes": {
            "n1": {"status": "SUCCESS", "attempts": 1},
            "n2": {"status": "SUCCESS", "attempts": 1},
            "n3": {"status": "SUCCESS", "attempts": 1},
        },
    }
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline_payload, indent=2), encoding="utf-8")

    out_path = tmp_path / "result.json"
    rc = main(["run", str(circuit_path), "--baseline", str(baseline_path), "--out", str(out_path)])
    assert rc == 2

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["policy"]["status"] == "FAIL"
    assert "display" in payload["policy"]
    assert payload["policy"]["display"].startswith("Status: FAIL")
    assert "Trigger: node n3" in payload["policy"]["display"]
