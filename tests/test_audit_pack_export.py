
from __future__ import annotations

import json
import zipfile

from src.cli.nexa_cli import build_parser, export_command
from src.engine.execution_audit_pack import ExecutionAuditPackBuilder


def _sample_run_payload() -> dict:
    return {
        "result": {
            "state": {
                "hello_node": {
                    "output": "Hello Nexa"
                }
            }
        },
        "summary": {
            "initial_state_keys": 1,
            "final_state_keys": 2,
            "node_outputs": 1,
            "produced_keys": ["hello_node"],
            "execution_time_ms": 1.2,
        },
        "trace": {
            "events": ["node_started", "node_completed"]
        },
        "artifacts": [
            {"name": "greeting", "value": "Hello Nexa"}
        ],
    }


def test_cli_parser_accepts_export_command():
    parser = build_parser()
    args = parser.parse_args(["export", "result.json", "--out", "audit.zip"])
    assert args.command == "export"
    assert args.input == "result.json"
    assert args.out == "audit.zip"


def test_audit_pack_export_creates_zip(tmp_path):
    out_file = tmp_path / "audit.zip"
    ExecutionAuditPackBuilder.export(_sample_run_payload(), str(out_file))
    assert out_file.exists()

    with zipfile.ZipFile(out_file, "r") as zf:
        names = set(zf.namelist())

    assert "execution_trace.json" in names
    assert "metadata.json" in names
    assert "summary.json" in names
    assert "replay_payload.json" in names
    assert "artifacts/artifact_1.json" in names


def test_audit_pack_export_trace_content_is_deterministic(tmp_path):
    out_a = tmp_path / "audit_a.zip"
    out_b = tmp_path / "audit_b.zip"

    payload = _sample_run_payload()
    ExecutionAuditPackBuilder.export(payload, str(out_a))
    ExecutionAuditPackBuilder.export(payload, str(out_b))

    with zipfile.ZipFile(out_a, "r") as zf:
        trace_a = zf.read("execution_trace.json")
    with zipfile.ZipFile(out_b, "r") as zf:
        trace_b = zf.read("execution_trace.json")

    assert trace_a == trace_b


def test_export_command_reads_result_json_and_writes_zip(tmp_path):
    input_file = tmp_path / "result.json"
    out_file = tmp_path / "audit.zip"
    input_file.write_text(json.dumps(_sample_run_payload(), indent=2), encoding="utf-8")

    class Args:
        input = str(input_file)
        out = str(out_file)

    rc = export_command(Args())
    assert rc == 0
    assert out_file.exists()


def test_audit_pack_export_includes_execution_record_reference_contract_when_present(tmp_path):
    out_file = tmp_path / "audit.zip"
    payload = _sample_run_payload()
    payload["execution_record_reference_contract"] = {
        "primary_trace_ref": "events://hello-exec",
        "is_replay_ready": True,
        "is_audit_ready": True,
    }

    ExecutionAuditPackBuilder.export(payload, str(out_file))

    with zipfile.ZipFile(out_file, "r") as zf:
        names = set(zf.namelist())
        metadata = json.loads(zf.read("metadata.json").decode("utf-8"))
        contract = json.loads(zf.read("execution_record_reference_contract.json").decode("utf-8"))

    assert "execution_record_reference_contract.json" in names
    assert metadata["replay_ready"] is True
    assert metadata["audit_ready"] is True
    assert metadata["primary_trace_ref"] == "events://hello-exec"
    assert contract["primary_trace_ref"] == "events://hello-exec"
