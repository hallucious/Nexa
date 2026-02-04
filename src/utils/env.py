from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(dotenv_path: Path | None = None) -> None:
    """
    Minimal .env loader (stdlib-only).
    - Lines: KEY=VALUE
    - Ignores empty lines and comments (#)
    - Does NOT override existing os.environ values
    """
    if dotenv_path is None:
        dotenv_path = Path(".env")

    if not dotenv_path.exists():
        return

    try:
        for line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception:
        # Fail silently by design
        return
