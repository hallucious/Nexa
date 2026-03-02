from __future__ import annotations

"""Legacy gates shim.

Canonical legacy implementation moved to:
    src.legacy.gates.g2_continuity

Engine-native execution does not use gates directly.
"""

import importlib as _importlib

_legacy = _importlib.import_module("src.legacy.gates.g2_continuity")

for _k, _v in _legacy.__dict__.items():
    # Avoid overwriting module identity attributes (__file__, __spec__, etc.)
    if _k.startswith("__") and _k.endswith("__"):
        continue
    globals()[_k] = _v
