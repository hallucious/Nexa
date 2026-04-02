
from __future__ import annotations

import json
import zipfile

from src.cli.nexa_cli import build_parser, replay_command
from src.engine.audit_replay import replay_audit_pack
from src.engine.execution_audit_pack import ExecutionAuditPackBuilder


def _sample_run_payload() -> dict:
    return {
        "result": {
            "state": {
                "hello_node": {"output": "Hello Nexa"},
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
            "events": ["node_started", "node_completed"],
        },
        "artifacts": [
            {"name": "greeting", "value": "Hello Nexa"},
        ],
        "replay_payload": {
            "execution_id": "hello-exec",
            "node_order": ["hello_node"],
            "circuit": {
                "id": "hello-circuit",
                "nodes": [
                    {
                        "id": "hello_node",
                        "execution_config_ref": "cfg.hello",
                        "depends_on": [],
                    }
                ],
            },
            "execution_configs": {
                "cfg.hello": {
                    "config_id": "cfg.hello",
                    "provider_ref": "echo",
                    "provider_inputs": {
                        "message": "input.message"
                    },
                }
            },
            "input_state": {"message": "Hello Nexa"},
            "expected_outputs": {
                "hello_node": "Hello Nexa",
            },
        },
    }


def test_cli_parser_accepts_replay_command():
    parser = build_parser()
    args = parser.parse_args(["replay", "audit.zip"])
    assert args.command == "replay"
    assert args.input == "audit.zip"
    assert args.strict is False


def test_replay_audit_pack_passes_for_matching_payload(tmp_path):
    audit_zip = tmp_path / "audit.zip"
    ExecutionAuditPackBuilder.export(_sample_run_payload(), str(audit_zip))

    result = replay_audit_pack(str(audit_zip))
    assert result["status"] == "PASS"
    assert result["differences"] == []


def test_replay_audit_pack_fails_for_mismatched_expected_output(tmp_path):
    audit_zip = tmp_path / "audit.zip"
    payload = _sample_run_payload()
    payload["replay_payload"]["expected_outputs"]["hello_node"] = "Wrong Value"
    ExecutionAuditPackBuilder.export(payload, str(audit_zip))

    result = replay_audit_pack(str(audit_zip))
    assert result["status"] == "FAIL"
    assert any("node hello_node" in diff for diff in result["differences"])


def test_replay_command_errors_when_replay_payload_missing(tmp_path):
    audit_zip = tmp_path / "audit.zip"
    payload = {
        "result": {"state": {}},
        "summary": {},
        "trace": {},
        "artifacts": [],
    }
    ExecutionAuditPackBuilder.export(payload, str(audit_zip))

    class Args:
        input = str(audit_zip)
        strict = False

    rc = replay_command(Args())
    assert rc == 1


def test_export_includes_replay_payload_file(tmp_path):
    out_file = tmp_path / "audit.zip"
    ExecutionAuditPackBuilder.export(_sample_run_payload(), str(out_file))

    with zipfile.ZipFile(out_file, "r") as zf:
        names = set(zf.namelist())
        replay_payload = json.loads(zf.read("replay_payload.json").decode("utf-8"))
        contract = json.loads(zf.read("execution_record_reference_contract.json").decode("utf-8"))

    assert "replay_payload.json" in names
    assert "execution_record_reference_contract.json" in names
    assert replay_payload["execution_id"] == "hello-exec"
    assert contract["is_replay_ready"] is True


def test_replay_audit_pack_uses_execution_record_reference_contract(tmp_path):
    audit_zip = tmp_path / "audit.zip"
    payload = _sample_run_payload()
    payload["execution_record_reference_contract"] = {
        "primary_trace_ref": "events://hello-exec",
        "is_replay_ready": True,
        "is_audit_ready": True,
    }
    ExecutionAuditPackBuilder.export(payload, str(audit_zip))

    result = replay_audit_pack(str(audit_zip))
    assert result["status"] == "PASS"
    assert result["primary_trace_ref"] == "events://hello-exec"
    assert result["reference_contract"]["is_replay_ready"] is True


def test_replay_audit_pack_fails_when_reference_contract_is_not_replay_ready(tmp_path):
    audit_zip = tmp_path / "audit.zip"
    payload = _sample_run_payload()
    payload["execution_record_reference_contract"] = {
        "primary_trace_ref": "events://hello-exec",
        "is_replay_ready": False,
        "is_audit_ready": True,
    }
    ExecutionAuditPackBuilder.export(payload, str(audit_zip))

    result = replay_audit_pack(str(audit_zip))
    assert result["status"] == "FAIL"
    assert "execution record reference contract is not replay-ready" in result["differences"]


def test_replay_audit_pack_derives_reference_contract_from_execution_record_when_contract_file_missing(tmp_path):
    from src.engine.execution_snapshot import ExecutionSnapshotBuilder
    from src.engine.execution_artifact_hashing import ExecutionHashReport, NodeOutputHash
    from src.engine.execution_timeline import ExecutionTimeline, NodeExecutionSpan
    from src.storage.execution_record_api import create_execution_record_from_snapshot
    from src.storage.serialization import serialize_execution_record

    payload = _sample_run_payload()
    timeline = ExecutionTimeline(
        execution_id='hello-exec',
        start_ms=1000,
        end_ms=1200,
        duration_ms=200,
        node_spans=[NodeExecutionSpan('hello_node', 1000, 1200, 200, 'success')],
    )
    snapshot = ExecutionSnapshotBuilder().build(
        execution_id='hello-exec',
        timeline=timeline,
        outputs={'hello_node': 'Hello Nexa'},
        hash_report=ExecutionHashReport(execution_id='hello-exec', node_hashes=[NodeOutputHash(node_id='hello_node', algorithm='sha256', hash_value='abc')]),
    )
    record = create_execution_record_from_snapshot(snapshot, commit_id='commit-1', trace_ref='trace://hello-exec', event_stream_ref='events://hello-exec')
    payload['execution_record'] = serialize_execution_record(record)

    audit_zip = tmp_path / 'audit.zip'
    ExecutionAuditPackBuilder.export(payload, str(audit_zip))

    derived_zip = tmp_path / 'audit_no_contract.zip'
    with zipfile.ZipFile(audit_zip, 'r') as src_zip, zipfile.ZipFile(derived_zip, 'w', compression=zipfile.ZIP_DEFLATED) as dst_zip:
        for name in src_zip.namelist():
            if name == 'execution_record_reference_contract.json':
                continue
            dst_zip.writestr(name, src_zip.read(name))

    result = replay_audit_pack(str(derived_zip))
    assert result['status'] == 'PASS'
    assert result['reference_contract']['primary_trace_ref'] == 'events://hello-exec'
    assert result['execution_record']['meta']['run_id'] == 'hello-exec'
