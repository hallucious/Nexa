from __future__ import annotations

import json
from pathlib import Path

from src.cli.nexa_cli import build_parser, diff_command
from src.engine.execution_diff_engine import compare_runs
from src.engine.execution_diff_formatter import format_diff, format_diff_json


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_step208_compare_runs_projects_verifier_aware_changes() -> None:
    left = {
        "run_id": "run-left",
        "nodes": {
            "draft": {
                "status": "success",
                "output": {"text": "alpha"},
                "verifier_status": "warning",
                "verifier_reason_codes": ["REQUIREMENT_TEXT_TOO_SHORT"],
            }
        },
        "artifacts": {
            "artifact::report": {
                "hash": "hash-a",
                "kind": "validation_report",
                "validation_status": "warning",
                "artifact_schema_version": "1.0.0",
            }
        },
        "observability": {
            "verifier_summary": {"verifier_report_count": 1, "status_counts": {"warning": 1}}
        },
    }
    right = {
        "run_id": "run-right",
        "nodes": {
            "draft": {
                "status": "success",
                "output": {"text": "alpha"},
                "verifier_status": "pass",
                "verifier_reason_codes": [],
            }
        },
        "artifacts": {
            "artifact::report": {
                "hash": "hash-a",
                "kind": "validation_report",
                "validation_status": "pass",
                "artifact_schema_version": "1.1.0",
            }
        },
        "observability": {
            "verifier_summary": {"verifier_report_count": 1, "status_counts": {"pass": 1}}
        },
    }

    diff = compare_runs(left, right)

    assert diff.summary.verification_changes == 3
    assert any(item.target_type == "node" and item.target_id == "draft" for item in diff.verification_diffs)
    assert any(item.target_type == "artifact" and item.target_id == "artifact::report" for item in diff.verification_diffs)
    assert any(item.target_type == "run" and item.target_id == "verifier_summary" for item in diff.verification_diffs)

    rendered = format_diff(diff)
    assert "verification_changes: 3" in rendered
    assert "Verification Changes" in rendered
    assert "verifier:" in rendered

    payload = format_diff_json(diff)
    assert payload["summary"]["verification_changes"] == 3
    assert len(payload["verification"]) == 3
    assert payload["nodes"][0]["left_verifier_status"] == "warning"
    assert payload["artifacts"][0]["left_validation_status"] == "warning"


def test_step208_cli_diff_json_surfaces_execution_record_verifier_changes(tmp_path, capsys) -> None:
    left = {
        "execution_record": {
            "meta": {"run_id": "run-left"},
            "node_results": {
                "results": [
                    {
                        "node_id": "draft",
                        "status": "success",
                        "output_preview": "alpha",
                        "artifact_refs": ["artifact::report"],
                        "typed_artifact_refs": ["artifact::typed"],
                        "verifier_status": "warning",
                        "verifier_reason_codes": ["REQUIREMENT_TEXT_TOO_SHORT"],
                    }
                ]
            },
            "artifacts": {
                "artifact_refs": [
                    {
                        "artifact_id": "artifact::report",
                        "artifact_type": "validation_report",
                        "validation_status": "warning",
                        "artifact_schema_version": "1.0.0",
                    },
                    {
                        "artifact_id": "artifact::typed",
                        "artifact_type": "json_object",
                        "validation_status": "warning",
                        "artifact_schema_version": "1.0.0",
                    },
                ]
            },
            "observability": {
                "verifier_summary": {"verifier_report_count": 1, "status_counts": {"warning": 1}}
            },
        }
    }
    right = {
        "execution_record": {
            "meta": {"run_id": "run-right"},
            "node_results": {
                "results": [
                    {
                        "node_id": "draft",
                        "status": "success",
                        "output_preview": "alpha",
                        "artifact_refs": ["artifact::report"],
                        "typed_artifact_refs": ["artifact::typed"],
                        "verifier_status": "pass",
                        "verifier_reason_codes": [],
                    }
                ]
            },
            "artifacts": {
                "artifact_refs": [
                    {
                        "artifact_id": "artifact::report",
                        "artifact_type": "validation_report",
                        "validation_status": "pass",
                        "artifact_schema_version": "1.1.0",
                    },
                    {
                        "artifact_id": "artifact::typed",
                        "artifact_type": "json_object",
                        "validation_status": "pass",
                        "artifact_schema_version": "1.0.0",
                    },
                ]
            },
            "observability": {
                "verifier_summary": {"verifier_report_count": 1, "status_counts": {"pass": 1}}
            },
        }
    }

    left_path = _write(tmp_path / "left.json", left)
    right_path = _write(tmp_path / "right.json", right)

    args = build_parser().parse_args(["diff", str(left_path), str(right_path), "--json"])
    code = diff_command(args)

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["verification_changes"] == 4
    assert any(item["target_type"] == "node" for item in payload["verification"])
    assert any(item["target_type"] == "run" for item in payload["verification"])
