"""
DEPRECATED (Legacy Pipeline Stabilization Invariants)

This test suite is pipeline/runner/decision-artifact specific:
- RunStatus PASS/STOP semantics
- Decision artifacts (Gx_DECISION.md)
- "UNKNOWN decision" policy
- max_attempts_per_gate loop guard (runner retry loop)
- stop_reason normalization (INTERNAL_ERROR)

These concepts do NOT exist in Engine DAG execution (Engine executes a DAG; no gate-loop retry),
and are replaced by Engine-level contracts:
- Validation failure -> NOT_REACHED: tests/test_engine_validation_policy_contract.py
- Handler exception -> FAILURE + downstream SKIPPED: tests/test_engine_node_handlers.py
- Failure propagation -> SKIPPED: tests/test_engine_failure_policy_contract.py
- Trace minimum contract: tests/test_engine_trace_min_contract.py

Kept temporarily for migration traceability.
"""

import pytest

pytest.skip(
    "Deprecated legacy pipeline stabilization invariants. Engine DAG contracts cover the applicable safety semantics.",
    allow_module_level=True,
)
