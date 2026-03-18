import json
from pathlib import Path

from src.cli.nexa_cli import (
    append_observability_record,
    build_failure_observability_record,
    build_success_observability_record,
)


class DummyArgs:
    command = "run"
    circuit = "examples/sample.nex"
    configs = "configs"
    plugins = "plugins"


def test_append_observability_record_writes_jsonl(tmp_path, monkeypatch):
    obs_file = tmp_path / "OBSERVABILITY.jsonl"
    monkeypatch.setattr("src.cli.nexa_cli.OBSERVABILITY_FILE", obs_file)

    record = {
        "timestamp": 123.456,
        "command": "run",
        "circuit_path": "examples/sample.nex",
        "circuit_id": "sample-circuit",
        "status": "success",
        "success": True,
        "execution_time_ms": 12.3,
        "node_count": 3,
        "executed_nodes": 3,
        "wave_count": 2,
        "plugin_calls": 1,
        "provider_calls": 1,
        "error_type": None,
        "error_message": None,
    }

    append_observability_record(record)

    assert obs_file.exists()

    lines = obs_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1

    loaded = json.loads(lines[0])
    assert loaded == record


def test_build_success_observability_record_uses_runtime_metrics():
    args = DummyArgs()
    circuit = {
        "id": "sample-circuit",
        "nodes": [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}],
    }
    metrics = {
        "executed_nodes": 3,
        "wave_count": 2,
        "plugin_calls": 4,
        "provider_calls": 5,
    }

    record = build_success_observability_record(
        args=args,
        circuit=circuit,
        metrics=metrics,
        started_at=10.0,
        ended_at=10.25,
    )

    assert record["command"] == "run"
    assert record["circuit_path"] == "examples/sample.nex"
    assert record["circuit_id"] == "sample-circuit"
    assert record["status"] == "success"
    assert record["success"] is True
    assert record["node_count"] == 3
    assert record["executed_nodes"] == 3
    assert record["wave_count"] == 2
    assert record["plugin_calls"] == 4
    assert record["provider_calls"] == 5
    assert record["error_type"] is None
    assert record["error_message"] is None
    assert record["execution_time_ms"] == 250.0


def test_build_failure_observability_record_captures_exception():
    args = DummyArgs()
    exc = ValueError("bad input")

    record = build_failure_observability_record(args=args, exc=exc)

    assert record["command"] == "run"
    assert record["circuit_path"] == "examples/sample.nex"
    assert record["circuit_id"] is None
    assert record["status"] == "error"
    assert record["success"] is False
    assert record["execution_time_ms"] is None
    assert record["node_count"] is None
    assert record["executed_nodes"] is None
    assert record["wave_count"] is None
    assert record["plugin_calls"] is None
    assert record["provider_calls"] is None
    assert record["error_type"] == "ValueError"
    assert record["error_message"] == "bad input"
    assert isinstance(record["timestamp"], float)