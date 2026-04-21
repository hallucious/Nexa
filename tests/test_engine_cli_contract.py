
"""
Engine CLI Contract Test

Goal:
- Establish a minimal, stable contract for the new Engine CLI surface.
- No legacy imports required.
"""

from __future__ import annotations

from typing import List


def test_engine_cli_dry_run_returns_zero_and_prints(capsys):
    from src.cli.engine_cli import main

    rc = main(["--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Dry run successful" in out


def test_engine_cli_default_returns_zero_and_prints(capsys):
    from src.cli.engine_cli import main

    rc = main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Execution placeholder" in out
