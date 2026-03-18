"""
test_node_failure_propagation_policy.py

Contract tests for NodeFailurePolicy v1.

Covers:
1. STRICT (default) — preserves existing behavior
2. ISOLATE — upstream FAILURE does not automatically skip downstream
3. CASCADE_FAIL — upstream FAILURE immediately marks downstream FAILURE
4. Default unchanged when node_failure_policies not provided
"""
from __future__ import annotations

import pytest

from src.engine.engine import Engine
from src.engine.model import Channel
from src.engine.types import FlowPolicy, NodeFailurePolicy, NodeStatus
from src.engine.model import FlowRule


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _failing_handler(inp):
    raise RuntimeError("forced failure")


def _ok_handler(inp):
    return {"result": "ok"}


def _chain(n=2, *, fail_entry=True):
    """Build n-node chain n1→n2→...→n<n>.  Entry fails if fail_entry=True."""
    node_ids = [f"n{i+1}" for i in range(n)]
    channels = [
        Channel(channel_id=f"c{i}", src_node_id=node_ids[i], dst_node_id=node_ids[i+1])
        for i in range(n - 1)
    ]
    handlers = {node_ids[0]: _failing_handler if fail_entry else _ok_handler}
    # downstream nodes get no-op (default) handler
    return node_ids, channels, handlers


# ─────────────────────────────────────────────────────────────────────────────
# NodeFailurePolicy enum
# ─────────────────────────────────────────────────────────────────────────────

def test_node_failure_policy_values_exist():
    assert NodeFailurePolicy.STRICT.value == "STRICT"
    assert NodeFailurePolicy.ISOLATE.value == "ISOLATE"
    assert NodeFailurePolicy.CASCADE_FAIL.value == "CASCADE_FAIL"


# ─────────────────────────────────────────────────────────────────────────────
# 1. STRICT — default preserves existing behavior
# ─────────────────────────────────────────────────────────────────────────────

def test_strict_upstream_failure_skips_downstream_default():
    """Without any node_failure_policies, upstream failure skips downstream (ALL_SUCCESS)."""
    node_ids, channels, handlers = _chain(2)
    eng = Engine(entry_node_id="n1", node_ids=node_ids, channels=channels, handlers=handlers)
    trace = eng.execute(revision_id="r_strict_default")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n2"].node_status == NodeStatus.SKIPPED


def test_strict_explicit_same_as_default():
    """Explicitly setting STRICT must produce the same result as omitting the policy."""
    node_ids, channels, handlers = _chain(2)

    eng_default = Engine(entry_node_id="n1", node_ids=node_ids, channels=channels, handlers=handlers)
    eng_strict = Engine(
        entry_node_id="n1",
        node_ids=node_ids,
        channels=channels,
        handlers=handlers,
        node_failure_policies={"n2": NodeFailurePolicy.STRICT},
    )

    t_default = eng_default.execute(revision_id="r_d")
    t_strict = eng_strict.execute(revision_id="r_s")

    assert t_default.nodes["n2"].node_status == t_strict.nodes["n2"].node_status == NodeStatus.SKIPPED


def test_strict_three_node_chain_propagates_skip():
    """Upstream failure cascades as SKIPPED through STRICT chain."""
    node_ids, channels, handlers = _chain(3)
    eng = Engine(entry_node_id="n1", node_ids=node_ids, channels=channels, handlers=handlers)
    trace = eng.execute(revision_id="r_chain3")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n2"].node_status == NodeStatus.SKIPPED
    assert trace.nodes["n3"].node_status == NodeStatus.SKIPPED


# ─────────────────────────────────────────────────────────────────────────────
# 2. ISOLATE — upstream failure does not auto-skip downstream
# ─────────────────────────────────────────────────────────────────────────────

def test_isolate_upstream_failure_does_not_skip_downstream():
    """ISOLATE: upstream FAILURE is not treated as a blocking signal; node gets SKIPPED
    only when no success is available (not because of FAILURE alone)."""
    node_ids, channels, handlers = _chain(2)
    eng = Engine(
        entry_node_id="n1",
        node_ids=node_ids,
        channels=channels,
        handlers=handlers,
        node_failure_policies={"n2": NodeFailurePolicy.ISOLATE},
    )
    trace = eng.execute(revision_id="r_isolate")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    # With ISOLATE and only one parent (n1=FAILURE), n2 ends up SKIPPED
    # (isolated failure = no success available) but NOT via ENG-UPSTREAM-FAIL.
    # The important thing: it's not skipped via the STRICT upstream-fail path.
    n2 = trace.nodes["n2"]
    # It should be skipped because no success can be found, not because failure is blocking
    assert n2.node_status in (NodeStatus.SKIPPED, NodeStatus.FAILURE)
    # Must NOT use the STRICT skip reason code
    if n2.node_status == NodeStatus.SKIPPED:
        assert n2.reason_code != "ENG-UPSTREAM-FAIL"


def test_isolate_downstream_executes_when_any_upstream_succeeds():
    """ISOLATE: node runs when FlowPolicy (ANY_SUCCESS) is satisfied by a non-failed parent.

    Topology: entry(ok) → n2(fail-chain-start) → n3(isolate, ANY_SUCCESS)
              entry(ok) also flows → n3 directly (to give n3 a success parent).
    """
    # entry(ok) → n2(fail), entry(ok) → n3(isolate+ANY_SUCCESS)
    node_ids = ["entry", "n2", "n3"]
    channels = [
        Channel(channel_id="c1", src_node_id="entry", dst_node_id="n2"),
        Channel(channel_id="c2", src_node_id="entry", dst_node_id="n3"),
        Channel(channel_id="c3", src_node_id="n2", dst_node_id="n3"),
    ]
    handlers = {"n2": _failing_handler}
    flow = [FlowRule(rule_id="r1", node_id="n3", policy=FlowPolicy.ANY_SUCCESS)]
    eng = Engine(
        entry_node_id="entry",
        node_ids=node_ids,
        channels=channels,
        handlers=handlers,
        flow=flow,
        node_failure_policies={"n3": NodeFailurePolicy.ISOLATE},
    )
    trace = eng.execute(revision_id="r_isolate_any")

    assert trace.nodes["entry"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n2"].node_status == NodeStatus.FAILURE
    # n3 has parents entry(SUCCESS) + n2(FAILURE); with ISOLATE, n2's failure is
    # masked; ANY_SUCCESS is satisfied by entry → n3 should run
    assert trace.nodes["n3"].node_status == NodeStatus.SUCCESS


def test_isolate_all_parents_terminal_and_no_success_results_in_skip():
    """ISOLATE: when all parents are terminal with no success, downstream still skips."""
    # entry(fail) → n2(isolate); only parent is entry(FAILURE); no success available
    node_ids = ["entry", "n2"]
    channels = [Channel(channel_id="c1", src_node_id="entry", dst_node_id="n2")]
    handlers = {"entry": _failing_handler}
    eng = Engine(
        entry_node_id="entry",
        node_ids=node_ids,
        channels=channels,
        handlers=handlers,
        node_failure_policies={"n2": NodeFailurePolicy.ISOLATE},
    )
    trace = eng.execute(revision_id="r_isolate_all_fail")

    assert trace.nodes["n2"].node_status == NodeStatus.SKIPPED


# ─────────────────────────────────────────────────────────────────────────────
# 3. CASCADE_FAIL — upstream failure marks downstream FAILURE
# ─────────────────────────────────────────────────────────────────────────────

def test_cascade_fail_upstream_failure_marks_downstream_failure():
    """CASCADE_FAIL: upstream FAILURE immediately marks downstream as FAILURE."""
    node_ids, channels, handlers = _chain(2)
    executed = []

    def tracked_handler(inp):
        executed.append(True)
        return {"result": "ok"}

    handlers["n2"] = tracked_handler

    eng = Engine(
        entry_node_id="n1",
        node_ids=node_ids,
        channels=channels,
        handlers=handlers,
        node_failure_policies={"n2": NodeFailurePolicy.CASCADE_FAIL},
    )
    trace = eng.execute(revision_id="r_cascade")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n2"].node_status == NodeStatus.FAILURE
    assert not executed, "handler must not execute under CASCADE_FAIL"


def test_cascade_fail_handler_is_not_executed():
    """CASCADE_FAIL: handler never runs; output_snapshot is None."""
    node_ids, channels, handlers = _chain(2)
    eng = Engine(
        entry_node_id="n1",
        node_ids=node_ids,
        channels=channels,
        handlers=handlers,
        node_failure_policies={"n2": NodeFailurePolicy.CASCADE_FAIL},
    )
    trace = eng.execute(revision_id="r_cascade_no_exec")

    n2 = trace.nodes["n2"]
    assert n2.node_status == NodeStatus.FAILURE
    assert n2.output_snapshot is None


def test_cascade_fail_reason_code_recorded():
    """CASCADE_FAIL: ENG-CASCADE-FAIL reason code is recorded in the node trace."""
    node_ids, channels, handlers = _chain(2)
    eng = Engine(
        entry_node_id="n1",
        node_ids=node_ids,
        channels=channels,
        handlers=handlers,
        node_failure_policies={"n2": NodeFailurePolicy.CASCADE_FAIL},
    )
    trace = eng.execute(revision_id="r_cascade_code")

    n2 = trace.nodes["n2"]
    assert n2.reason_code == "ENG-CASCADE-FAIL"
    assert n2.message is not None and "upstream" in n2.message.lower()


def test_cascade_fail_does_not_block_engine_execution():
    """CASCADE_FAIL on one node does not prevent the engine from completing."""
    # n1(fail) → n2(cascade), n1 → n3(strict, unaffected)
    node_ids = ["n1", "n2", "n3"]
    channels = [
        Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2"),
        Channel(channel_id="c2", src_node_id="n1", dst_node_id="n3"),
    ]
    handlers = {"n1": _failing_handler}
    eng = Engine(
        entry_node_id="n1",
        node_ids=node_ids,
        channels=channels,
        handlers=handlers,
        node_failure_policies={"n2": NodeFailurePolicy.CASCADE_FAIL},
    )
    trace = eng.execute(revision_id="r_cascade_engine_ok")

    # Engine returned a trace; n1 failed; n2 cascade-failed; n3 skipped (STRICT default)
    assert trace is not None
    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n2"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n3"].node_status == NodeStatus.SKIPPED


def test_cascade_fail_only_triggers_on_failure_not_skip():
    """CASCADE_FAIL fires only on upstream FAILURE, not SKIPPED."""
    # n1(ok) → n2(fail) → n3(cascade_fail)
    # n2 is SKIPPED because n1 ok but n2 has no handler -> actually n2 runs with noop
    # Let's build: n0(fail) → n1(strict, gets skipped) → n2(cascade_fail)
    node_ids = ["n0", "n1", "n2"]
    channels = [
        Channel(channel_id="c1", src_node_id="n0", dst_node_id="n1"),
        Channel(channel_id="c2", src_node_id="n1", dst_node_id="n2"),
    ]
    handlers = {"n0": _failing_handler}
    eng = Engine(
        entry_node_id="n0",
        node_ids=node_ids,
        channels=channels,
        handlers=handlers,
        node_failure_policies={"n2": NodeFailurePolicy.CASCADE_FAIL},
    )
    trace = eng.execute(revision_id="r_cascade_skip_only")

    # n1 becomes SKIPPED (STRICT default, n0 failed)
    assert trace.nodes["n1"].node_status == NodeStatus.SKIPPED
    # n2's only parent is n1 (SKIPPED, not FAILURE) → CASCADE_FAIL should NOT fire
    # n2 should be SKIPPED (by STRICT-like downstream logic, not FAILURE)
    assert trace.nodes["n2"].node_status != NodeStatus.FAILURE or \
           trace.nodes["n2"].reason_code != "ENG-CASCADE-FAIL", \
           "CASCADE_FAIL must only fire on upstream FAILURE, not SKIPPED"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Default unchanged when node_failure_policies not provided
# ─────────────────────────────────────────────────────────────────────────────

def test_no_policy_field_engine_behaves_identically():
    """Omitting node_failure_policies entirely produces the same result as {}."""
    node_ids, channels, handlers = _chain(3)

    eng1 = Engine(entry_node_id="n1", node_ids=node_ids, channels=channels, handlers=handlers)
    eng2 = Engine(
        entry_node_id="n1",
        node_ids=node_ids,
        channels=channels,
        handlers=handlers,
        node_failure_policies={},
    )

    t1 = eng1.execute(revision_id="r1")
    t2 = eng2.execute(revision_id="r2")

    for nid in node_ids:
        assert t1.nodes[nid].node_status == t2.nodes[nid].node_status


def test_engine_level_validation_unaffected():
    """Engine-level validation lifecycle is unaffected by node_failure_policies."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        node_failure_policies={"n1": NodeFailurePolicy.CASCADE_FAIL},
    )
    trace = eng.execute(revision_id="r_val")
    assert trace.validation_success is True
    assert "validation" in trace.meta
    assert "pre_validation" in trace.meta
    assert "post_validation" in trace.meta
    assert "decision" in trace.meta


def test_mixed_policies_on_different_nodes():
    """Different failure policies can coexist on different downstream nodes."""
    # n1(fail) → n2(cascade_fail), n1 → n3(isolate), n1 → n4(strict default)
    node_ids = ["n1", "n2", "n3", "n4"]
    channels = [
        Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2"),
        Channel(channel_id="c2", src_node_id="n1", dst_node_id="n3"),
        Channel(channel_id="c3", src_node_id="n1", dst_node_id="n4"),
    ]
    handlers = {"n1": _failing_handler}
    eng = Engine(
        entry_node_id="n1",
        node_ids=node_ids,
        channels=channels,
        handlers=handlers,
        node_failure_policies={
            "n2": NodeFailurePolicy.CASCADE_FAIL,
            "n3": NodeFailurePolicy.ISOLATE,
            # n4 has no policy → STRICT default
        },
    )
    trace = eng.execute(revision_id="r_mixed")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n2"].node_status == NodeStatus.FAILURE   # cascade
    assert trace.nodes["n3"].node_status == NodeStatus.SKIPPED   # isolate, all parents terminal no success
    assert trace.nodes["n4"].node_status == NodeStatus.SKIPPED   # strict default
