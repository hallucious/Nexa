from __future__ import annotations

import os
from pathlib import Path

from src.pipeline import cli


def test_cli_loads_dotenv_best_effort(tmp_path: Path, monkeypatch):
    # Create a temp project root with a .env
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=TESTKEY123\n", encoding="utf-8")

    # Ensure environment is clean
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # Run loader in that cwd
    monkeypatch.chdir(tmp_path)
    cli._load_dotenv_if_available(cwd=tmp_path)

    # If python-dotenv is installed, key must be present.
    # If not installed, loader is no-op, so we accept missing.
    # However, in this project dotenv is expected, so we assert it if import works.
    try:
        import dotenv  # noqa: F401
    except Exception:
        assert os.getenv("OPENAI_API_KEY") is None
    else:
        assert os.getenv("OPENAI_API_KEY") == "TESTKEY123"
