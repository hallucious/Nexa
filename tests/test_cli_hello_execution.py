"""
test_cli_hello_execution.py

Verifies that `nexa run examples/hello_world.nex` executes successfully:
  - exit code 0
  - output contains "Hello Nexa"
  - no exceptions raised
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from io import StringIO

import pytest

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
NEX_FILE = ROOT / "examples" / "hello_world.nex"


def _run_cli(*argv):
    """Invoke run_command directly and capture stdout.

    Returns (exit_code, stdout_text).
    """
    from src.cli.nexa_cli import build_parser, run_command

    parser = build_parser()
    args = parser.parse_args(["run", str(NEX_FILE), *argv])

    captured = StringIO()
    original_stdout = sys.stdout
    sys.stdout = captured
    try:
        exit_code = run_command(args)
    except SystemExit as exc:
        exit_code = exc.code
    finally:
        sys.stdout = original_stdout

    return exit_code, captured.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Required contract tests
# ─────────────────────────────────────────────────────────────────────────────

def test_hello_execution_exit_code_zero():
    """CLI returns exit code 0 on successful execution."""
    assert NEX_FILE.exists(), f"hello_world.nex not found at {NEX_FILE}"
    exit_code, _ = _run_cli()
    assert exit_code == 0


def test_hello_execution_output_contains_hello_nexa():
    """CLI output contains 'Hello Nexa'."""
    _, output = _run_cli()
    assert "Hello Nexa" in output, f"Expected 'Hello Nexa' in output:\n{output}"


def test_hello_execution_no_exception():
    """CLI does not raise an exception (output is valid JSON, not error payload)."""
    _, output = _run_cli()
    data = json.loads(output)
    assert "status" not in data or data.get("status") != "error", (
        f"CLI returned an error payload:\n{output}"
    )


def test_hello_execution_output_is_valid_json():
    """CLI output is well-formed JSON."""
    _, output = _run_cli()
    data = json.loads(output)
    assert isinstance(data, dict)


def test_hello_execution_result_contains_state():
    """CLI output payload has a result.state dict."""
    _, output = _run_cli()
    data = json.loads(output)
    assert "result" in data
    assert "state" in data["result"]
    assert isinstance(data["result"]["state"], dict)


def test_hello_execution_summary_present():
    """CLI output payload includes a summary section."""
    _, output = _run_cli()
    data = json.loads(output)
    assert "summary" in data
    summary = data["summary"]
    assert "node_outputs" in summary
    assert summary["node_outputs"] >= 1


def test_hello_nex_file_loads_correctly():
    """The .nex file is a valid circuit accepted by CircuitSchemaValidator."""
    from src.circuit.circuit_io import load_circuit
    circuit = load_circuit(str(NEX_FILE))
    assert isinstance(circuit, dict)
    assert "nodes" in circuit
    assert len(circuit["nodes"]) >= 1
