"""
DEPRECATED (Legacy Pipeline Observability Contract)

This test validates PipelineRunner-based observability hooks.
Engine uses ExecutionTrace as immutable execution evidence instead of runner-level events.

Replaced by:
- tests/test_engine_trace_min_contract.py
- tests/test_engine_failure_policy_contract.py

Kept temporarily for migration traceability.
"""

import pytest

pytest.skip(
    "Deprecated legacy pipeline observability contract. Engine trace contract supersedes it.",
    allow_module_level=True,
)
