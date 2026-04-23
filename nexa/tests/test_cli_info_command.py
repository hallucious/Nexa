"""
Tests for `nexa info` CLI command.

Validates:
1. command executes without error (exit code 0)
2. output contains "Nexa System Info"
3. output contains all expected fields
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from src.cli.nexa_cli import get_system_info, info_command


# ---------------------------------------------------------------------------
# Unit — get_system_info()
# ---------------------------------------------------------------------------

def test_get_system_info_returns_dict():
    info = get_system_info()
    assert isinstance(info, dict)


def test_get_system_info_python_version():
    info = get_system_info()
    version = info["python_version"]
    assert isinstance(version, str)
    major, minor = version.split(".")
    assert int(major) >= 3
    assert int(minor) >= 0


def test_get_system_info_nexa_root_exists():
    from pathlib import Path
    info = get_system_info()
    root = Path(info["nexa_root"])
    assert root.exists(), f"Nexa root path does not exist: {root}"


def test_get_system_info_providers_installed_is_non_negative():
    info = get_system_info()
    assert isinstance(info["providers_installed"], int)
    assert info["providers_installed"] >= 0


def test_get_system_info_plugins_registered_is_non_negative():
    info = get_system_info()
    assert isinstance(info["plugins_registered"], int)
    assert info["plugins_registered"] >= 0


# ---------------------------------------------------------------------------
# Unit — info_command() prints expected output
# ---------------------------------------------------------------------------

def test_info_command_returns_zero(capsys):
    exit_code = info_command()
    assert exit_code == 0


def test_info_command_output_contains_header(capsys):
    info_command()
    captured = capsys.readouterr()
    assert "Nexa System Info" in captured.out


def test_info_command_output_contains_separator(capsys):
    info_command()
    captured = capsys.readouterr()
    assert "----------------" in captured.out


def test_info_command_output_contains_python_version(capsys):
    info_command()
    captured = capsys.readouterr()
    assert "Python Version:" in captured.out


def test_info_command_output_contains_nexa_root(capsys):
    info_command()
    captured = capsys.readouterr()
    assert "Nexa Root Path:" in captured.out


def test_info_command_output_contains_providers(capsys):
    info_command()
    captured = capsys.readouterr()
    assert "Providers Installed:" in captured.out


def test_info_command_output_contains_plugins(capsys):
    info_command()
    captured = capsys.readouterr()
    assert "Plugins Registered:" in captured.out


# ---------------------------------------------------------------------------
# Integration — subprocess `nexa info`
# ---------------------------------------------------------------------------

def test_cli_info_command_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "src.cli.nexa_cli", "info"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI exited non-zero:\n{result.stderr}"


def test_cli_info_command_output_contains_system_info():
    result = subprocess.run(
        [sys.executable, "-m", "src.cli.nexa_cli", "info"],
        capture_output=True,
        text=True,
    )
    assert "Nexa System Info" in result.stdout


def test_cli_info_command_output_contains_all_fields():
    result = subprocess.run(
        [sys.executable, "-m", "src.cli.nexa_cli", "info"],
        capture_output=True,
        text=True,
    )
    output = result.stdout
    assert "Python Version:" in output
    assert "Nexa Root Path:" in output
    assert "Providers Installed:" in output
    assert "Plugins Registered:" in output
