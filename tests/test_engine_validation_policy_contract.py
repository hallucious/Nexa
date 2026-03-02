
"""
T1: Engine Validation Failure Contract

Purpose:
Freeze validation → NOT_REACHED semantics before removing legacy validation tests.

Invariant:
If validation fails, no node should be executed,
and all nodes must remain NOT_REACHED.
"""

from __future__ import annotations

from src.engine.engine import Engine
from src.engine.types import NodeStatus


def test_validation_failure_results_in_all_not_reached():
    # Invalid engine: empty entry_node_id triggers validation failure
    eng = Engine(
        entry_node_id="",
        node_ids=["n1", "n2"],
    )

    trace = eng.execute(revision_id="r_invalid")

    assert trace.validation_success is False

    for node in trace.nodes.values():
        assert node.node_status == NodeStatus.NOT_REACHED
