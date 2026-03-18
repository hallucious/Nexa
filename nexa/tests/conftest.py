from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure repo root is importable for tests
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (no external deps).

    - Does not override existing environment variables.
    - Supports KEY=VALUE lines; ignores blanks and comments.
    """
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if not k:
                continue
            if os.environ.get(k) is None:
                os.environ[k] = v
    except Exception:
        # If .env can't be read/parsed, let tests fail normally (missing keys).
        return


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--real-api",
        action="store_true",
        default=False,
        help="Run real API integration tests (requires provider API keys in env or .env).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: tests that make real external API calls (run only with --real-api)",
    )
    config.addinivalue_line(
        "markers",
        "contract: internal contract tests (documentation/code invariants)",
    )

    # When user explicitly requests real API tests, automatically load .env from repo root.
    if config.getoption("--real-api"):
        _load_dotenv(REPO_ROOT / ".env")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    # Default: do NOT run external API calls unless explicitly requested.
    if config.getoption("--real-api"):
        return

    skip_integration = pytest.mark.skip(reason="real API tests require --real-api")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
