from __future__ import annotations

import json

from src.engine.cli import build_parser, main


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


def test_engine_cli_parser_accepts_run_and_out():
    parser = build_parser()
    args = parser.parse_args(["run", "example.nex", "--out", "result.json"])
    assert args.command == "run"
    assert args.circuit == "example.nex"
    assert args.out == "result.json"


def test_engine_cli_run_writes_summary_json(tmp_path):
    circuit_path = tmp_path / "example.nex"
    out_path = tmp_path / "result.json"
    circuit_path.write_text(json.dumps(_example_nex_dict(), indent=2), encoding="utf-8")

    rc = main(["run", str(circuit_path), "--out", str(out_path)])
    assert rc == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["circuit_id"] == "demo.story_pipeline"
    assert payload["status"] == "SUCCESS"
    assert payload["nodes"]["n1"]["status"] == "SUCCESS"
    assert payload["nodes"]["n2"]["status"] == "SUCCESS"


def test_engine_cli_run_prints_summary_without_out(tmp_path, capsys):
    circuit_path = tmp_path / "example.nex"
    circuit_path.write_text(json.dumps(_example_nex_dict(), indent=2), encoding="utf-8")

    rc = main(["run", str(circuit_path)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["circuit_id"] == "demo.story_pipeline"
    assert payload["status"] == "SUCCESS"
