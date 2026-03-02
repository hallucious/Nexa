from __future__ import annotations

import json
import subprocess
import sys

import pytest


@pytest.mark.contract
def test_engine_does_not_import_legacy_pipeline_modules() -> None:
    """Engine must not depend on legacy pipeline/gates/orchestrator modules.

    Rationale:
    - We are migrating from pipeline -> engine.
    - Legacy modules may remain temporarily, but Engine must be import-isolated.
    - This is enforced in a fresh Python process to avoid cross-test contamination.
    """
    code = r'''
import json
import sys

# Import engine (minimal)
from src.engine.engine import Engine  # noqa: F401

legacy_prefixes = ("src.pipeline", "src.gates", "src.platform.orchestrator")
legacy_loaded = sorted([m for m in sys.modules.keys() if m.startswith(legacy_prefixes)])
print(json.dumps({"legacy_loaded": legacy_loaded}))
'''

    out = subprocess.check_output([sys.executable, "-c", code], text=True)
    data = json.loads(out.strip() or "{}")
    legacy_loaded = data.get("legacy_loaded", [])
    assert legacy_loaded == [], f"Engine import pulled legacy modules: {legacy_loaded}"
