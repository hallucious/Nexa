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
