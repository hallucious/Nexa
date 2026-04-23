from __future__ import annotations

import json
import zipfile

from src.cli.engine_cli import build_parser, main


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



def _example_savefile_dict():
    return {
        "meta": {
            "name": "demo.savefile_pipeline",
            "version": "1.0.0",
            "description": "Minimal savefile example for engine CLI tests",
        },
        "circuit": {
            "entry": "ai1",
            "nodes": [
                {
                    "id": "ai1",
                    "type": "ai",
                    "resource_ref": {"prompt": "prompt.main", "provider": "provider.test"},
                    "inputs": {"name": "state.input.name"},
                    "outputs": {},
                }
            ],
            "edges": [],
        },
        "resources": {
            "prompts": {"prompt.main": {"template": "Hello {{name}}"}},
            "providers": {
                "provider.test": {"type": "test", "model": "test-model", "config": {}}
            },
            "plugins": {},
        },
        "state": {"input": {"name": "Nexa"}, "working": {}, "memory": {}},
        "ui": {"layout": {}, "metadata": {}},
    }

def test_engine_cli_parser_accepts_baseline_flag():
    parser = build_parser()
    args = parser.parse_args(["run", "example.nex", "--baseline", "baseline.json"])
    assert args.command == "run"
    assert args.circuit == "example.nex"
    assert args.baseline == "baseline.json"


def test_engine_cli_run_with_clean_baseline_returns_zero_and_emits_policy(tmp_path):
    circuit_path = tmp_path / "example.nex"
    circuit_path.write_text(json.dumps(_example_nex_dict(), indent=2), encoding="utf-8")

    baseline_payload = {
        "circuit_id": "demo.story_pipeline",
        "status": "SUCCESS",
        "nodes": {
            "n1": {"status": "SUCCESS", "attempts": 1},
            "n2": {"status": "SUCCESS", "attempts": 1},
        },
    }
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline_payload, indent=2), encoding="utf-8")

    out_path = tmp_path / "result.json"
    rc = main(["run", str(circuit_path), "--baseline", str(baseline_path), "--out", str(out_path)])
    assert rc == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["circuit_id"] == "demo.story_pipeline"
    assert payload["policy"]["status"] == "PASS"
    assert payload["policy"]["reasons"][0].startswith("PASS:")


def test_engine_cli_run_with_failure_regression_returns_two(tmp_path):
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
    assert any("Trigger: node n3" in reason for reason in payload["policy"]["reasons"])


def test_engine_cli_run_savefile_with_clean_baseline_returns_zero_and_emits_policy(tmp_path):
    circuit_path = tmp_path / "savefile.nex"
    circuit_path.write_text(json.dumps(_example_savefile_dict(), indent=2), encoding="utf-8")

    baseline_payload = {
        "circuit_id": "demo.savefile_pipeline",
        "status": "SUCCESS",
        "nodes": {
            "ai1": {"status": "SUCCESS", "attempts": 1},
        },
    }
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline_payload, indent=2), encoding="utf-8")

    out_path = tmp_path / "result.json"
    rc = main(["run", str(circuit_path), "--baseline", str(baseline_path), "--out", str(out_path)])
    assert rc == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["circuit_id"] == "demo.savefile_pipeline"
    assert payload["policy"]["status"] == "PASS"
    assert payload["policy"]["reasons"][0].startswith("PASS:")


def test_engine_cli_run_savefile_bundle_with_clean_baseline_returns_zero_and_emits_policy(tmp_path):
    bundle_path = tmp_path / "savefile.nexb"

    temp = tmp_path / "bundle_build"
    temp.mkdir()
    (temp / "circuit.nex").write_text(json.dumps(_example_savefile_dict(), indent=2), encoding="utf-8")

    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.write(temp / "circuit.nex", "circuit.nex")

    baseline_payload = {
        "circuit_id": "demo.savefile_pipeline",
        "status": "SUCCESS",
        "nodes": {
            "ai1": {"status": "SUCCESS", "attempts": 1},
        },
    }
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline_payload, indent=2), encoding="utf-8")

    out_path = tmp_path / "result.json"
    rc = main(["run", str(bundle_path), "--baseline", str(baseline_path), "--out", str(out_path)])
    assert rc == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["circuit_id"] == "demo.savefile_pipeline"
    assert payload["policy"]["status"] == "PASS"
    assert payload["policy"]["reasons"][0].startswith("PASS:")
