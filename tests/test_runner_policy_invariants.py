"""
DEPRECATED (Legacy Pipeline Failure/Policy Invariants)

This legacy runner-based policy invariant test is deprecated.
Replaced by Engine-level contracts:

- tests/test_engine_failure_policy_contract.py
- tests/test_engine_validation_policy_contract.py

Kept temporarily for migration traceability.
"""

import pytest

pytest.skip(
    "Deprecated legacy pipeline policy invariants. Use Engine policy contracts instead.",
    allow_module_level=True,
)
