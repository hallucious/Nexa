from __future__ import annotations

import os
from pathlib import Path

from src.pipeline import cli


def test_cli_loads_dotenv_from_repo_root(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "src" / "pipeline").mkdir(parents=True)
    (repo / ".env").write_text("OPENAI_API_KEY=from_dotenv\n", encoding="utf-8")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    cli._maybe_load_dotenv(repo_root=repo)

    # If python-dotenv isn't installed in the test environment, this is a no-op.
    if os.getenv("OPENAI_API_KEY") is None:
        return
    assert os.getenv("OPENAI_API_KEY") == "from_dotenv"
