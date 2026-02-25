from __future__ import annotations

import importlib
from pathlib import Path

from src.platform.plugin_discovery import discovered_ids
from src.platform.plugin_registry import as_mapping


def _repo_root() -> Path:
    # tests run from repo root in our harness; keep fallback for safety.
    here = Path(__file__).resolve()
    for parent in [here.parent] + list(here.parents):
        if (parent / "src").exists() and (parent / "tests").exists():
            return parent
    return Path.cwd()


def test_hybrid_registry_matches_discovery_exactly() -> None:
    """Hybrid invariant (v0.1): scan and registry must match.

    This catches:
    - orphan plugin files (file exists but not registered)
    - missing files (registered but file missing)

    Note: gates are allowed to have *no* plugin. That is represented by
    simply not having a *_plugin.py file and not registering an entry.
    """

    root = _repo_root()
    discovered = discovered_ids(root)
    registry_ids = set(as_mapping().keys())

    orphan = sorted(discovered - registry_ids)
    missing = sorted(registry_ids - discovered)

    assert orphan == [], f"Orphan plugin files found (scan but not registry): {orphan}"
    assert missing == [], f"Registry entries missing corresponding files: {missing}"


def test_registered_plugins_expose_required_symbols() -> None:
    """Contract: each registry entry must be importable and expose its symbols."""

    reg = as_mapping()
    for pid, c in reg.items():
        mod = importlib.import_module(c.module)
        for sym in c.required_symbols:
            assert hasattr(mod, sym), f"{pid}: missing required symbol '{sym}' in {c.module}"
