from __future__ import annotations

"""Legacy pipeline CLI shim.

Canonical legacy implementation moved to:
    src.legacy.pipeline_cli

Engine-native execution entrypoint is:
    src.engine.cli
"""

import importlib as _importlib

_legacy = _importlib.import_module("src.legacy.pipeline_cli")

# Re-export everything (including private symbols used by tests)
globals().update(_legacy.__dict__)
