from __future__ import annotations

import json
import zipfile
from pathlib import Path

from src.cli.nexa_cli import build_parser, replay_command
from src.engine.audit_replay import replay_audit_pack


def _write_json(root: Path, name: str, payload: dict) -> None:
    (root / name).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _build_replay_zip(path: Path, *, replay_outputs: dict[str, str], include_replay_payload: bool = True) -> None:
    root = path.parent / (path.stem + "_dir")
    root.mkdir(parents=True, exist_ok=True)
    (root / "artifacts").mkdir(exist_ok=True)

    _write_json(root, "execution_trace.json", {"events": ["execution_started", "execution_completed"]})
    _write_json(root, "metadata.json", {"format": "nexa.audit_pack", "version": "1.0.0"})
    _write_json(root, "summary.json", {"artifact_count": 0, "state_keys": 3})

    if include_replay_payload:
        _write_json(root, "replay_payload.json", {
            "timeline": {
                "execution_id": "exec-1",
                "start_ms": 0,
                "end_ms": 50,
                "duration_ms": 50,
                "node_spans": [
                    {"node_id": "node_a", "start_ms": 10, "end_ms": 20, "duration_ms": 10, "status": "success"},
                    {"node_id": "node_b", "start_ms": 25, "end_ms": 40, "duration_ms": 15, "status": "success"},
                ],
            },
            "circuit": {
                "id": "sample-circuit",
                "nodes": [
                    {"id": "node_a", "execution_config_ref": "cfg.a", "depends_on": []},
                    {"id": "node_b", "execution_config_ref": "cfg.b", "depends_on": ["node_a"]},
                ],
            },
            "input_state": {"question": "x"},
            "expected_outputs": {"node_a": "output-a", "node_b": "output-b"},
            "configs": {"cfg.a": {"config_id": "cfg.a"}, "cfg.b": {"config_id": "cfg.b"}},
            "replay_outputs": replay_outputs,
        })

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(root.rglob("*")):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(root))


def test_cli_parser_accepts_replay_command():
    parser = build_parser()
    args = parser.parse_args(["replay", "audit.zip"])
    assert args.command == "replay"
    assert args.audit_zip == "audit.zip"
    assert args.strict is False


def test_replay_audit_pack_returns_pass(tmp_path):
    audit_zip = tmp_path / "audit.zip"
    _build_replay_zip(audit_zip, replay_outputs={"cfg.a": "output-a", "cfg.b": "output-b"})

    result = replay_audit_pack(str(audit_zip))

    assert result["status"] == "PASS"
    assert result["differences"] == []


def test_replay_audit_pack_returns_fail_on_modified_output(tmp_path):
    audit_zip = tmp_path / "audit.zip"
    _build_replay_zip(audit_zip, replay_outputs={"cfg.a": "output-a", "cfg.b": "wrong-b"})

    result = replay_audit_pack(str(audit_zip))

    assert result["status"] == "FAIL"
    assert result["differences"][0]["node_id"] == "node_b"


def test_replay_command_handles_missing_replay_payload_gracefully(tmp_path):
    audit_zip = tmp_path / "audit.zip"
    _build_replay_zip(audit_zip, replay_outputs={"cfg.a": "output-a", "cfg.b": "output-b"}, include_replay_payload=False)

    class Args:
        strict = True

    args = Args()
    args.audit_zip = str(audit_zip)

    rc = replay_command(args)
    assert rc == 1
