"""
DEPRECATED (Legacy Pipeline META Snapshot Contract)

This test validates PipelineRunner-specific META.json snapshot semantics.
Engine uses ExecutionTrace as the structural execution evidence instead of META.json.

Replaced by:
- tests/test_engine_trace_min_contract.py
- tests/test_engine_repeatability_contract.py

Kept temporarily for migration traceability.
"""

import pytest

pytest.skip(
    "Deprecated legacy runner META snapshot contract. Engine trace contract supersedes it.",
    allow_module_level=True,
)
