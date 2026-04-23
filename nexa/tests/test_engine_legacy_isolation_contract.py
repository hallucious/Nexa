from __future__ import annotations

import importlib
import json
import subprocess
import sys

import pytest


@pytest.mark.contract
def test_engine_does_not_import_legacy_pipeline_modules() -> None:
    """Engine must not depend on any removed legacy modules.

    Verified in a fresh subprocess to avoid cross-test contamination.
    src.pipeline, src.gates, src.legacy, and src.platform.orchestrator
    have been physically removed — any re-introduction is a regression.
    """
    code = r'''
import json
import sys

from src.engine.engine import Engine  # noqa: F401

forbidden_prefixes = ("src.pipeline", "src.gates", "src.legacy", "src.platform.orchestrator")
found = sorted([m for m in sys.modules.keys() if m.startswith(forbidden_prefixes)])
print(json.dumps({"found": found}))
'''

    out = subprocess.check_output([sys.executable, "-c", code], text=True)
    data = json.loads(out.strip() or "{}")
    found = data.get("found", [])
    assert found == [], f"Engine import pulled forbidden legacy modules: {found}"


def test_legacy_packages_are_physically_absent() -> None:
    """Confirm that removed packages cannot be imported at all."""
    for pkg in ("src.pipeline", "src.gates", "src.legacy"):
        try:
            importlib.import_module(pkg)
            raise AssertionError(f"{pkg} must not be importable after legacy removal")
        except ModuleNotFoundError:
            pass  # correct — package is gone
