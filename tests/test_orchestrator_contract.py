"""
DEPRECATED (Legacy GateOrchestrator Contract)

This test validates src.platform.orchestrator (pipeline-era GateOrchestrator).
Engine DAG execution model replaces orchestrator-based composition.

Replaced by Engine graph + ExecutionTrace contracts:
- tests/test_engine_trace_min_contract.py
- tests/test_engine_failure_policy_contract.py

Kept temporarily for migration traceability before physical removal.
"""

import pytest

pytest.skip(
    "Deprecated legacy GateOrchestrator contract. Engine DAG model supersedes it.",
    allow_module_level=True,
)
