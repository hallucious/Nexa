"""
tests/test_cli_diff_command.py

CLI tests for the `nexa diff` command (Step182).

Covers:
1. diff command success with identical runs
2. diff command success with changed runs
3. summary output contains required fields
4. missing file returns non-zero
5. invalid JSON returns non-zero
6. non-dict JSON payload returns non-zero
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.cli.nexa_cli import build_parser, diff_command, _load_run_snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_run(tmp_path: Path, name: str, data: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _identical_run(run_id: str = "r1") -> dict:
    return {
        "run_id": run_id,
        "nodes": {"n1": {"status": "success", "output": "hello"}},
    }


def _changed_run(run_id: str = "r2") -> dict:
    return {
        "run_id": run_id,
        "nodes": {
            "n1": {"status": "failure", "output": "different"},
            "n2": {"status": "success"},
        },
        "artifacts": {"art_1": {"hash": "h1", "kind": "provider_output"}},
        "context": {"input.text.value": "world"},
    }


# ---------------------------------------------------------------------------
# Parser registration
# ---------------------------------------------------------------------------

def test_diff_parser_registered():
    parser = build_parser()
    args = parser.parse_args(["diff", "left.json", "right.json"])
    assert args.command == "diff"
    assert args.left == "left.json"
    assert args.right == "right.json"


# ---------------------------------------------------------------------------
# 1. Identical runs → status=identical
# ---------------------------------------------------------------------------

def test_diff_identical_runs(tmp_path, capsys):
    left_path = _write_run(tmp_path, "left.json", _identical_run("r1"))
    right_path = _write_run(tmp_path, "right.json", _identical_run("r1"))

    args = build_parser().parse_args(["diff", str(left_path), str(right_path)])
    code = diff_command(args)

    assert code == 0
    out = capsys.readouterr().out
    assert "status: identical" in out


# ---------------------------------------------------------------------------
# 2. Changed runs → status=changed
# ---------------------------------------------------------------------------

def test_diff_changed_runs(tmp_path, capsys):
    left_path = _write_run(tmp_path, "left.json", _identical_run("r1"))
    right_path = _write_run(tmp_path, "right.json", _changed_run("r2"))

    args = build_parser().parse_args(["diff", str(left_path), str(right_path)])
    code = diff_command(args)

    assert code == 0
    out = capsys.readouterr().out
    assert "status: changed" in out


# ---------------------------------------------------------------------------
# 3. Summary output contains required fields
# ---------------------------------------------------------------------------

def test_diff_output_contains_required_fields(tmp_path, capsys):
    left_path = _write_run(tmp_path, "left.json", _identical_run("r1"))
    right_path = _write_run(tmp_path, "right.json", _changed_run("r2"))

    args = build_parser().parse_args(["diff", str(left_path), str(right_path)])
    diff_command(args)

    out = capsys.readouterr().out
    assert "Execution Diff" in out
    assert "status:" in out
    assert "nodes:" in out
    assert "added=" in out
    assert "removed=" in out
    assert "changed=" in out
    assert "artifacts:" in out
    assert "context_keys_changed:" in out


def test_diff_summary_numbers_match_engine(tmp_path, capsys):
    left = _identical_run("r1")
    right = _changed_run("r2")

    left_path = _write_run(tmp_path, "left.json", left)
    right_path = _write_run(tmp_path, "right.json", right)

    from src.engine.execution_diff_engine import compare_runs
    expected = compare_runs(left, right)

    args = build_parser().parse_args(["diff", str(left_path), str(right_path)])
    diff_command(args)
    out = capsys.readouterr().out

    assert f"added={expected.summary.nodes_added}" in out
    assert f"removed={expected.summary.nodes_removed}" in out
    assert f"context_keys_changed: {expected.summary.context_keys_changed}" in out


# ---------------------------------------------------------------------------
# 4. Missing file → SystemExit(1) / non-zero
# ---------------------------------------------------------------------------

def test_diff_missing_left_file_raises(tmp_path):
    right_path = _write_run(tmp_path, "right.json", _identical_run())
    args = build_parser().parse_args([
        "diff", str(tmp_path / "nonexistent.json"), str(right_path)
    ])
    with pytest.raises(SystemExit) as exc_info:
        diff_command(args)
    assert exc_info.value.code != 0


def test_diff_missing_right_file_raises(tmp_path):
    left_path = _write_run(tmp_path, "left.json", _identical_run())
    args = build_parser().parse_args([
        "diff", str(left_path), str(tmp_path / "nonexistent.json")
    ])
    with pytest.raises(SystemExit) as exc_info:
        diff_command(args)
    assert exc_info.value.code != 0


def test_diff_missing_file_subprocess_returns_nonzero(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "src.cli.nexa_cli", "diff",
         str(tmp_path / "no.json"), str(tmp_path / "no.json")],
        capture_output=True, text=True,
    )
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# 5. Invalid JSON → non-zero
# ---------------------------------------------------------------------------

def test_diff_invalid_json_left(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    right_path = _write_run(tmp_path, "right.json", _identical_run())

    args = build_parser().parse_args(["diff", str(bad), str(right_path)])
    with pytest.raises(SystemExit) as exc_info:
        diff_command(args)
    assert exc_info.value.code != 0


def test_diff_invalid_json_right(tmp_path):
    left_path = _write_run(tmp_path, "left.json", _identical_run())
    bad = tmp_path / "bad.json"
    bad.write_text("[unclosed", encoding="utf-8")

    args = build_parser().parse_args(["diff", str(left_path), str(bad)])
    with pytest.raises(SystemExit) as exc_info:
        diff_command(args)
    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# 6. Non-dict JSON payload → non-zero
# ---------------------------------------------------------------------------

def test_diff_non_dict_left(tmp_path):
    bad = tmp_path / "list.json"
    bad.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    right_path = _write_run(tmp_path, "right.json", _identical_run())

    args = build_parser().parse_args(["diff", str(bad), str(right_path)])
    with pytest.raises(SystemExit) as exc_info:
        diff_command(args)
    assert exc_info.value.code != 0


def test_diff_non_dict_right(tmp_path):
    left_path = _write_run(tmp_path, "left.json", _identical_run())
    bad = tmp_path / "str.json"
    bad.write_text(json.dumps("just a string"), encoding="utf-8")

    args = build_parser().parse_args(["diff", str(left_path), str(bad)])
    with pytest.raises(SystemExit) as exc_info:
        diff_command(args)
    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# _load_run_snapshot unit tests
# ---------------------------------------------------------------------------

def test_load_run_snapshot_valid(tmp_path):
    p = _write_run(tmp_path, "snap.json", {"run_id": "r1"})
    data = _load_run_snapshot(str(p))
    assert data == {"run_id": "r1"}


def test_load_run_snapshot_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        _load_run_snapshot(str(tmp_path / "ghost.json"))
    assert exc_info.value.code != 0


def test_load_run_snapshot_invalid_json_exits(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{bad", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        _load_run_snapshot(str(bad))
    assert exc_info.value.code != 0


def test_load_run_snapshot_non_dict_exits(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[1,2]", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        _load_run_snapshot(str(p))
    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# Subprocess integration — nexa diff
# ---------------------------------------------------------------------------

def test_diff_subprocess_identical(tmp_path):
    left_path = _write_run(tmp_path, "l.json", _identical_run("r1"))
    right_path = _write_run(tmp_path, "r.json", _identical_run("r1"))

    result = subprocess.run(
        [sys.executable, "-m", "src.cli.nexa_cli", "diff",
         str(left_path), str(right_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Execution Diff" in result.stdout
    assert "status: identical" in result.stdout


def test_diff_subprocess_changed(tmp_path):
    left_path = _write_run(tmp_path, "l.json", _identical_run("r1"))
    right_path = _write_run(tmp_path, "r.json", _changed_run("r2"))

    result = subprocess.run(
        [sys.executable, "-m", "src.cli.nexa_cli", "diff",
         str(left_path), str(right_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "status: changed" in result.stdout
