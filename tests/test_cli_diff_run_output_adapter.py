import json
import subprocess
import tempfile
from pathlib import Path


def _write_json_file(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_diff_normalizes_standard_run_output_and_detects_change():
    left_run = {
        "status": "success",
        "result": {
            "execution_id": "run-left",
            "state": {
                "summarizer_node": {
                    "output": "Alpha summary"
                }
            },
        },
        "replay_payload": {
            "execution_id": "run-left",
            "expected_outputs": {
                "output": "Alpha summary"
            },
        },
    }

    right_run = {
        "status": "success",
        "result": {
            "execution_id": "run-right",
            "state": {
                "summarizer_node": {
                    "output": "Beta summary"
                }
            },
        },
        "replay_payload": {
            "execution_id": "run-right",
            "expected_outputs": {
                "output": "Beta summary"
            },
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        left_path = Path(tmpdir) / "left.json"
        right_path = Path(tmpdir) / "right.json"
        _write_json_file(left_path, left_run)
        _write_json_file(right_path, right_run)

        result = subprocess.run(
            [
                "python", "-m", "src.cli.nexa_cli",
                "diff",
                str(left_path),
                str(right_path),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "status: changed" in result.stdout.lower()
        assert "nodes: added=0 removed=0 changed=1" in result.stdout.lower()


def test_diff_preserves_existing_snapshot_contract():
    left_run = {
        "run_id": "left",
        "nodes": {
            "n1": {"status": "success", "output": "x"},
        },
        "artifacts": {},
        "context": {"n1.output": "x"},
    }

    right_run = {
        "run_id": "right",
        "nodes": {
            "n1": {"status": "success", "output": "x"},
        },
        "artifacts": {},
        "context": {"n1.output": "x"},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        left_path = Path(tmpdir) / "left.json"
        right_path = Path(tmpdir) / "right.json"
        _write_json_file(left_path, left_run)
        _write_json_file(right_path, right_run)

        result = subprocess.run(
            [
                "python", "-m", "src.cli.nexa_cli",
                "diff",
                str(left_path),
                str(right_path),
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "status: identical" in result.stdout.lower()


def test_diff_prefers_native_execution_record_truth_over_stale_replay_identity_and_outputs():
    from src.cli.nexa_cli import _normalize_run_output_to_snapshot
    from src.storage.execution_record_api import create_serialized_execution_record_from_circuit_run

    native_record = create_serialized_execution_record_from_circuit_run(
        {"id": "native-circuit", "nodes": [{"id": "native_node"}]},
        {"native_node": {"value": "native"}},
        execution_id="native-exec",
        trace={"events": ["started", "completed"]},
        commit_id="commit-native",
    )
    payload = {
        "execution_record": native_record,
        "replay_payload": {
            "execution_id": "stale-exec",
            "node_order": ["stale_node"],
            "expected_outputs": {"stale_node": {"value": "stale"}},
        },
        "result": {
            "state": {
                "stale_node": {"output": {"value": "stale"}},
            },
        },
    }

    snapshot = _normalize_run_output_to_snapshot(payload)

    assert snapshot["run_id"] == "native-exec"
    assert snapshot["nodes"]["native_node"]["output"] == {"value": "native"}
    assert "stale_node" not in snapshot["nodes"]
    assert snapshot["context"]["output.native_node"] == {"value": "native"}


def test_diff_fallback_uses_canonicalized_replay_payload_when_native_record_is_minimal():
    from src.cli.nexa_cli import _normalize_run_output_to_snapshot

    payload = {
        "execution_record": {
            "meta": {"run_id": "native-minimal"},
            "source": {"commit_id": "commit-native"},
        },
        "replay_payload": {
            "execution_id": "stale-exec",
            "expected_outputs": {"output": {"value": "stale"}},
        },
        "result": {
            "execution_id": "result-exec",
            "state": {
                "node_a": {"output": {"value": "from-state"}},
            },
        },
    }

    snapshot = _normalize_run_output_to_snapshot(payload)

    assert snapshot["run_id"] == "native-minimal"
    assert snapshot["nodes"]["node_a"]["output"] == {"value": "from-state"}
    assert snapshot["context"]["output.output"] == {"value": "stale"}
