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


def test_engine_cli_run_savefile_native_contract_writes_summary_json(tmp_path):
    circuit_path = tmp_path / "savefile.nex"
    out_path = tmp_path / "result.json"
    circuit_path.write_text(json.dumps(_example_savefile_dict(), indent=2), encoding="utf-8")

    rc = main(["run", str(circuit_path), "--out", str(out_path)])
    assert rc == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["circuit_id"] == "demo.savefile_pipeline"
    assert payload["status"] == "SUCCESS"
    assert payload["nodes"]["ai1"]["status"] == "SUCCESS"


def test_engine_cli_run_savefile_bundle_writes_summary_json(tmp_path):
    bundle_path = tmp_path / "savefile.nexb"
    out_path = tmp_path / "result.json"

    temp = tmp_path / "bundle_build"
    temp.mkdir()
    (temp / "circuit.nex").write_text(json.dumps(_example_savefile_dict(), indent=2), encoding="utf-8")

    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.write(temp / "circuit.nex", "circuit.nex")

    rc = main(["run", str(bundle_path), "--out", str(out_path)])
    assert rc == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["circuit_id"] == "demo.savefile_pipeline"
    assert payload["status"] == "SUCCESS"
    assert payload["nodes"]["ai1"]["status"] == "SUCCESS"


def test_engine_cli_run_legacy_bundle_writes_summary_json(tmp_path):
    bundle_path = tmp_path / "legacy.nexb"
    out_path = tmp_path / "result.json"

    temp = tmp_path / "legacy_bundle"
    temp.mkdir()
    (temp / "plugins").mkdir()
    plugin_dir = temp / "plugins" / "text.cleaner"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "plugin_id": "text.cleaner",
                "version": "1.0.0",
                "entrypoint": "plugin.py:run",
                "type": "node",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (temp / "circuit.nex").write_text(json.dumps(_example_nex_dict(), indent=2), encoding="utf-8")

    with zipfile.ZipFile(bundle_path, "w") as zf:
        for path in temp.rglob("*"):
            zf.write(path, path.relative_to(temp))

    rc = main(["run", str(bundle_path), "--out", str(out_path)])
    assert rc == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["circuit_id"] == "demo.story_pipeline"
    assert payload["status"] == "SUCCESS"


def test_engine_cli_run_legacy_bundle_without_plugins_is_rejected(tmp_path):
    bundle_path = tmp_path / "legacy_missing_plugins.nexb"
    temp = tmp_path / "legacy_missing_plugins"
    temp.mkdir()
    (temp / "circuit.nex").write_text(json.dumps(_example_nex_dict(), indent=2), encoding="utf-8")

    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.write(temp / "circuit.nex", "circuit.nex")

    try:
        main(["run", str(bundle_path)])
        raise AssertionError("Expected RuntimeError for missing plugins/ in legacy bundle")
    except RuntimeError as exc:
        assert "plugins/ missing in bundle" in str(exc)


def test_engine_cli_run_legacy_nex_bundle_dir_allows_optional_missing_plugins(tmp_path):
    circuit = _example_nex_dict()
    circuit["plugins"] = [
        {"plugin_id": "text.cleaner", "version": "1.0.0", "required": True},
        {"plugin_id": "image.caption", "required": False},
    ]
    circuit_path = tmp_path / "example.nex"
    out_path = tmp_path / "result.json"
    circuit_path.write_text(json.dumps(circuit, indent=2), encoding="utf-8")

    bundle_root = tmp_path / "bundle_root"
    plugin_dir = bundle_root / "plugins" / "text.cleaner"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "plugin_id": "text.cleaner",
                "version": "1.0.0",
                "entrypoint": "plugin.py:run",
                "type": "node",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    rc = main(["run", str(circuit_path), "--bundle", str(bundle_root), "--out", str(out_path)])
    assert rc == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["status"] == "SUCCESS"


def test_engine_cli_run_legacy_nex_bundle_dir_rejects_plugin_version_mismatch(tmp_path):
    circuit_path = tmp_path / "example.nex"
    circuit_path.write_text(json.dumps(_example_nex_dict(), indent=2), encoding="utf-8")

    bundle_root = tmp_path / "bundle_root"
    plugin_dir = bundle_root / "plugins" / "text.cleaner"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "plugin_id": "text.cleaner",
                "version": "2.0.0",
                "entrypoint": "plugin.py:run",
                "type": "node",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        main(["run", str(circuit_path), "--bundle", str(bundle_root)])
        raise AssertionError("Expected RuntimeError for plugin version mismatch")
    except RuntimeError as exc:
        assert "Plugin version mismatch" in str(exc)
