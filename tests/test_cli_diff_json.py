"""
tests/test_cli_diff_json.py

CLI tests for nexa diff --json (Step185).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.cli.nexa_cli import build_parser, diff_command


def _write(tmp_path: Path, name: str, data: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _left() -> dict:
    return {"run_id": "r1", "nodes": {"n1": {"status": "success", "output": "hello"}}}


def _right_changed() -> dict:
    return {
        "run_id": "r2",
        "nodes": {
            "n1": {"status": "failure", "output": "world"},
            "n2": {"status": "success"},
        },
        "artifacts": {"art_1": {"hash": "h1", "kind": "provider_output"}},
        "context": {"input.text.value": "hi"},
    }


# --- parser registers --json ---

def test_diff_parser_has_json_flag():
    args = build_parser().parse_args(["diff", "a.json", "b.json", "--json"])
    assert args.output_json is True


def test_diff_parser_json_defaults_to_false():
    args = build_parser().parse_args(["diff", "a.json", "b.json"])
    assert args.output_json is False


# --- --json outputs valid JSON ---

def test_diff_json_output_is_valid_json(tmp_path, capsys):
    lp = _write(tmp_path, "l.json", _left())
    rp = _write(tmp_path, "r.json", _right_changed())
    args = build_parser().parse_args(["diff", str(lp), str(rp), "--json"])
    code = diff_command(args)
    assert code == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert isinstance(parsed, dict)


def test_diff_json_has_required_keys(tmp_path, capsys):
    lp = _write(tmp_path, "l.json", _left())
    rp = _write(tmp_path, "r.json", _right_changed())
    args = build_parser().parse_args(["diff", str(lp), str(rp), "--json"])
    diff_command(args)
    out = capsys.readouterr().out
    d = json.loads(out)
    for key in ("status", "summary", "nodes", "artifacts", "context"):
        assert key in d


def test_diff_json_status_changed(tmp_path, capsys):
    lp = _write(tmp_path, "l.json", _left())
    rp = _write(tmp_path, "r.json", _right_changed())
    args = build_parser().parse_args(["diff", str(lp), str(rp), "--json"])
    diff_command(args)
    d = json.loads(capsys.readouterr().out)
    assert d["status"] == "changed"


def test_diff_json_identical(tmp_path, capsys):
    lp = _write(tmp_path, "l.json", _left())
    rp = _write(tmp_path, "r.json", _left())
    args = build_parser().parse_args(["diff", str(lp), str(rp), "--json"])
    diff_command(args)
    d = json.loads(capsys.readouterr().out)
    assert d["status"] == "identical"
    assert d["nodes"] == []
    assert d["artifacts"] == []
    assert d["context"] == []


# --- without --json still prints text ---

def test_diff_without_json_prints_text(tmp_path, capsys):
    lp = _write(tmp_path, "l.json", _left())
    rp = _write(tmp_path, "r.json", _right_changed())
    args = build_parser().parse_args(["diff", str(lp), str(rp)])
    diff_command(args)
    out = capsys.readouterr().out
    assert "Execution Diff" in out
    assert "status:" in out


# --- subprocess ---

def test_diff_json_subprocess(tmp_path):
    lp = _write(tmp_path, "l.json", _left())
    rp = _write(tmp_path, "r.json", _right_changed())
    result = subprocess.run(
        [sys.executable, "-m", "src.cli.nexa_cli", "diff",
         str(lp), str(rp), "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    d = json.loads(result.stdout)
    assert d["status"] == "changed"
    assert isinstance(d["summary"], dict)
    assert isinstance(d["nodes"], list)
