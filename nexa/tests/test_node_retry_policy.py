"""
test_node_retry_policy.py

Contract tests for node_retry_policy (Node Retry Policy v1).

Execution order enforced:  primary → retry → fallback
"""
from __future__ import annotations

import pytest

from src.engine.engine import Engine, RetryConfig
from src.engine.model import Channel
from src.engine.types import NodeStatus


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fail(inp):
    raise RuntimeError("forced failure")


def _ok(inp):
    return {"result": "ok"}


class _CountingHandler:
    """Handler that fails the first N attempts then succeeds."""
    def __init__(self, fail_count: int):
        self.calls = 0
        self.fail_count = fail_count

    def __call__(self, inp):
        self.calls += 1
        if self.calls <= self.fail_count:
            raise RuntimeError(f"failing attempt {self.calls}")
        return {"attempt": self.calls, "result": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Retry succeeds before max_attempts
# ─────────────────────────────────────────────────────────────────────────────

def test_retry_succeeds_on_second_attempt():
    """Fails once, succeeds on second attempt; node ends as SUCCESS."""
    h = _CountingHandler(fail_count=1)
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": h},
        node_retry_policy={"n1": RetryConfig(max_attempts=3)},
    )
    trace = eng.execute(revision_id="r_retry_ok")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert h.calls == 2  # failed once, succeeded once


def test_retry_succeeds_on_first_attempt():
    """If first attempt succeeds, no further attempts are made."""
    h = _CountingHandler(fail_count=0)
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": h},
        node_retry_policy={"n1": RetryConfig(max_attempts=5)},
    )
    trace = eng.execute(revision_id="r_first_ok")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert h.calls == 1


# ─────────────────────────────────────────────────────────────────────────────
# 2. Retry fails → fallback succeeds
# ─────────────────────────────────────────────────────────────────────────────

def test_retry_fails_then_fallback_succeeds():
    """All retries fail, but fallback succeeds → node ends as SUCCESS."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup"],
        handlers={"n1": _fail, "n1_backup": _ok},
        node_retry_policy={"n1": RetryConfig(max_attempts=2)},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_retry_then_fb")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    # recovery meta must be present (fallback ran)
    assert "recovery" in trace.nodes["n1"].meta


# ─────────────────────────────────────────────────────────────────────────────
# 3. Retry fails → fallback fails
# ─────────────────────────────────────────────────────────────────────────────

def test_retry_and_fallback_both_fail():
    """All retries and fallback fail → node is FAILURE."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup"],
        handlers={"n1": _fail, "n1_backup": _fail},
        node_retry_policy={"n1": RetryConfig(max_attempts=2)},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_all_fail")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE


# ─────────────────────────────────────────────────────────────────────────────
# 4. Retry not configured → single execution
# ─────────────────────────────────────────────────────────────────────────────

def test_no_retry_policy_single_execution():
    """Without a retry policy, the handler runs exactly once."""
    call_log = []

    def handler(inp):
        call_log.append(True)
        return {"r": "ok"}

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": handler},
    )
    eng.execute(revision_id="r_no_retry")

    assert len(call_log) == 1


def test_no_retry_policy_failure_is_failure():
    """Without a retry policy, a failing node stays FAILURE."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": _fail},
    )
    trace = eng.execute(revision_id="r_no_retry_fail")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE


# ─────────────────────────────────────────────────────────────────────────────
# 5. Retry meta recorded correctly
# ─────────────────────────────────────────────────────────────────────────────

def test_retry_meta_structure_on_success():
    """retry meta block is correct when retry eventually succeeds."""
    h = _CountingHandler(fail_count=1)
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": h},
        node_retry_policy={"n1": RetryConfig(max_attempts=3)},
    )
    trace = eng.execute(revision_id="r_meta_ok")

    meta = trace.nodes["n1"].meta
    assert meta is not None
    assert "retry" in meta

    r = meta["retry"]
    assert r["attempted"] is True
    assert r["attempt_count"] == 2          # 1 fail + 1 success
    assert r["final_attempt"] == 1          # 0-based
    assert len(r["history"]) == 2
    assert r["history"][0] == {"attempt": 0, "status": "FAILURE"}
    assert r["history"][1] == {"attempt": 1, "status": "SUCCESS"}


def test_retry_meta_structure_all_fail():
    """retry meta block is correct when all attempts fail."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": _fail},
        node_retry_policy={"n1": RetryConfig(max_attempts=3)},
    )
    trace = eng.execute(revision_id="r_meta_fail")

    meta = trace.nodes["n1"].meta
    assert meta is not None
    assert "retry" in meta

    r = meta["retry"]
    assert r["attempted"] is True
    assert r["attempt_count"] == 3
    assert r["final_attempt"] == 2
    assert len(r["history"]) == 3
    assert all(h["status"] == "FAILURE" for h in r["history"])


def test_no_retry_meta_when_max_attempts_is_1():
    """max_attempts=1 must NOT produce a retry meta block."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": _ok},
        node_retry_policy={"n1": RetryConfig(max_attempts=1)},
    )
    trace = eng.execute(revision_id="r_ma1_meta")

    meta = trace.nodes["n1"].meta
    if meta is not None:
        assert "retry" not in meta


def test_no_retry_meta_when_policy_absent():
    """No retry policy → no retry meta block."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": _ok},
    )
    trace = eng.execute(revision_id="r_no_policy_meta")

    meta = trace.nodes["n1"].meta
    if meta is not None:
        assert "retry" not in meta


# ─────────────────────────────────────────────────────────────────────────────
# 6. Retry stops early on success
# ─────────────────────────────────────────────────────────────────────────────

def test_retry_stops_immediately_on_success():
    """Once a SUCCESS is returned, no further attempts are made."""
    h = _CountingHandler(fail_count=0)  # succeeds on first try
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": h},
        node_retry_policy={"n1": RetryConfig(max_attempts=10)},
    )
    trace = eng.execute(revision_id="r_early_stop")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert h.calls == 1  # stopped after first success

    r = trace.nodes["n1"].meta["retry"]
    assert r["attempt_count"] == 1


def test_retry_stops_after_second_success():
    """Fails twice, succeeds third; stops at third attempt."""
    h = _CountingHandler(fail_count=2)
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": h},
        node_retry_policy={"n1": RetryConfig(max_attempts=10)},
    )
    trace = eng.execute(revision_id="r_stop_third")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert h.calls == 3

    r = trace.nodes["n1"].meta["retry"]
    assert r["attempt_count"] == 3


# ─────────────────────────────────────────────────────────────────────────────
# 7. Retry uses same input_snapshot
# ─────────────────────────────────────────────────────────────────────────────

def test_retry_uses_same_input_snapshot():
    """All retry attempts receive the same (unmodified) input_snapshot."""
    received_inputs = []

    def capturing_handler(inp):
        received_inputs.append(dict(inp))
        raise RuntimeError("always fail")

    # Use a downstream node so we can control its input
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
        handlers={
            "n1": lambda inp: {"sentinel": 99},
            "n2": capturing_handler,
        },
        node_retry_policy={"n2": RetryConfig(max_attempts=3)},
    )
    eng.execute(revision_id="r_same_input")

    assert len(received_inputs) == 3
    # All three attempts received the exact same input
    assert received_inputs[0] == received_inputs[1] == received_inputs[2]
    # Input contains n1's output
    assert received_inputs[0]["n1"]["sentinel"] == 99


# ─────────────────────────────────────────────────────────────────────────────
# 8. max_attempts = 1 behaves like no retry
# ─────────────────────────────────────────────────────────────────────────────

def test_max_attempts_1_same_as_no_retry():
    """max_attempts=1 is functionally identical to not having a policy."""
    call_log = []

    def handler(inp):
        call_log.append(1)
        return {"r": "ok"}

    eng_none = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": handler},
    )
    eng_one = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": handler},
        node_retry_policy={"n1": RetryConfig(max_attempts=1)},
    )

    call_log.clear()
    t1 = eng_none.execute(revision_id="r_none")
    calls_none = len(call_log)

    call_log.clear()
    t2 = eng_one.execute(revision_id="r_one")
    calls_one = len(call_log)

    assert calls_none == calls_one == 1
    assert t1.nodes["n1"].node_status == t2.nodes["n1"].node_status == NodeStatus.SUCCESS


# ─────────────────────────────────────────────────────────────────────────────
# 9. invalid max_attempts (0) → FAILURE
# ─────────────────────────────────────────────────────────────────────────────

def test_max_attempts_zero_is_failure():
    """max_attempts=0 is a config error → FAILURE with reason code."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": _ok},
        node_retry_policy={"n1": RetryConfig(max_attempts=0)},
    )
    trace = eng.execute(revision_id="r_zero")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n1"].reason_code == "ENG-RETRY-INVALID-CONFIG"


def test_max_attempts_negative_is_failure():
    """Negative max_attempts is also a config error → FAILURE."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": _ok},
        node_retry_policy={"n1": RetryConfig(max_attempts=-1)},
    )
    trace = eng.execute(revision_id="r_neg")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n1"].reason_code == "ENG-RETRY-INVALID-CONFIG"


# ─────────────────────────────────────────────────────────────────────────────
# Integration: retry then fallback chain
# ─────────────────────────────────────────────────────────────────────────────

def test_retry_success_does_not_invoke_fallback():
    """When retry succeeds, fallback must NOT be called."""
    fallback_called = []

    def fallback(inp):
        fallback_called.append(True)
        return {"r": "fallback"}

    h = _CountingHandler(fail_count=1)
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n1_backup"],
        handlers={"n1": h, "n1_backup": fallback},
        node_retry_policy={"n1": RetryConfig(max_attempts=3)},
        node_fallback_map={"n1": "n1_backup"},
    )
    trace = eng.execute(revision_id="r_retry_no_fb")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert not fallback_called, "fallback must not be called when retry succeeds"
    assert "recovery" not in (trace.nodes["n1"].meta or {})


def test_downstream_success_after_retry_recovery():
    """After retry succeeds, downstream sees SUCCESS and executes."""
    h = _CountingHandler(fail_count=1)
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
        handlers={"n1": h, "n2": _ok},
        node_retry_policy={"n1": RetryConfig(max_attempts=3)},
    )
    trace = eng.execute(revision_id="r_downstream_retry")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n2"].node_status == NodeStatus.SUCCESS
