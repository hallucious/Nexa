from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEX_FILE = ROOT / "examples" / "hello_world.nex"
CONFIG_DIR = ROOT / "examples" / "execution_configs"


def _run_module_cli(*argv: str):
    command = [
        sys.executable,
        "-m",
        "src.cli.nexa_cli",
        "run",
        str(NEX_FILE),
        "--configs",
        str(CONFIG_DIR),
        *argv,
    ]
    return subprocess.run(command, capture_output=True, text=True, cwd=str(ROOT))


def test_hello_execution_exit_code_zero():
    result = _run_module_cli()
    assert result.returncode == 0, result.stderr


def test_hello_execution_output_contains_hello_nexa():
    result = _run_module_cli()
    assert "Hello Nexa" in result.stdout


def test_hello_execution_output_is_valid_json():
    result = _run_module_cli()
    payload = json.loads(result.stdout)
    assert isinstance(payload, dict)


def test_hello_execution_uses_external_config_directory():
    result = _run_module_cli()
    payload = json.loads(result.stdout)
    assert payload["result"]["state"]["hello_node"]["output"] == "Hello Nexa"
    assert CONFIG_DIR.exists()


def test_installed_entrypoint_runs_hello_example():
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["nexa", "run", str(NEX_FILE), "--configs", str(CONFIG_DIR)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, result.stderr
    assert "Hello Nexa" in result.stdout
