from __future__ import annotations

"""Legacy pipeline shim.

Canonical legacy implementation moved to:
    src.legacy.pipeline.registry

Engine-native execution entrypoint is:
    src.engine.cli
"""

import importlib as _importlib

_legacy = _importlib.import_module("src.legacy.pipeline.registry")

for _k, _v in _legacy.__dict__.items():
    if _k.startswith("__") and _k.endswith("__"):
        continue
    globals()[_k] = _v
