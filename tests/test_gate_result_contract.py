from __future__ import annotations

from dataclasses import fields

from src.pipeline.runner import GateResult


def test_gate_result_contract_structure():
    """
    Contract lock for GateResult structure.

    If this test fails, it means the core runner contract has changed and
    you MUST update:
    - docs/contracts/runner_state_transition_contract.md (if impacted)
    - any runner aggregation tests / snapshots
    """

    field_names = [f.name for f in fields(GateResult)]

    # Exact structural lock (order-sensitive)
    assert field_names == ["decision", "message", "outputs", "meta"]

    # Minimum presence guard (no instantiation to avoid ctor/default differences)
    for name in ["decision", "message", "outputs", "meta"]:
        assert name in field_names
