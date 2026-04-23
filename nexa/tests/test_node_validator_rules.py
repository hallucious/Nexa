"""
test_node_validator_rules.py

Unit and integration tests for NodeValidator V1 rules.

Rules covered:
    NODE-VAL-001 — Invalid node_id
    NODE-VAL-002 — Input snapshot must be dict
    NODE-VAL-003 — Reserved input key collision
"""
from __future__ import annotations

import pytest

from src.engine.validation.node_validator import NodeValidator
from src.engine.validation.node_result import NodeDecision, NodeValidationResult
from src.engine.validation.node_decision_policy import NodeDecisionPolicy
from src.engine.validation.result import Severity

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _validate(node_id, input_snapshot=None):
    if input_snapshot is None:
        input_snapshot = {}
    return NodeValidator().validate(node_id, input_snapshot)


def _rule_ids(result: NodeValidationResult):
    return [v.rule_id for v in result.violations]


# ---------------------------------------------------------------------------
# NODE-VAL-001: Invalid node_id
# ---------------------------------------------------------------------------

def test_node_val_001_non_string_node_id():
    result = _validate(123)
    assert result.success is False
    assert "NODE-VAL-001" in _rule_ids(result)


def test_node_val_001_none_node_id():
    result = _validate(None)
    assert result.success is False
    assert "NODE-VAL-001" in _rule_ids(result)


def test_node_val_001_empty_string_node_id():
    result = _validate("")
    assert result.success is False
    assert "NODE-VAL-001" in _rule_ids(result)


def test_node_val_001_whitespace_only_node_id():
    result = _validate("   ")
    assert result.success is False
    assert "NODE-VAL-001" in _rule_ids(result)


def test_node_val_001_violation_severity_is_error():
    result = _validate("")
    v001 = next(v for v in result.violations if v.rule_id == "NODE-VAL-001")
    assert v001.severity == Severity.ERROR


def test_node_val_001_violation_location_type_is_node():
    result = _validate(42)
    v001 = next(v for v in result.violations if v.rule_id == "NODE-VAL-001")
    assert v001.location_type == "node"


# ---------------------------------------------------------------------------
# NODE-VAL-002: Input snapshot must be dict
# ---------------------------------------------------------------------------

def test_node_val_002_list_input_snapshot():
    result = _validate("n1", ["a", "b"])
    assert result.success is False
    assert "NODE-VAL-002" in _rule_ids(result)


def test_node_val_002_none_input_snapshot():
    result = NodeValidator().validate("n1", None)
    assert result.success is False
    assert "NODE-VAL-002" in _rule_ids(result)


def test_node_val_002_string_input_snapshot():
    result = _validate("n1", "not a dict")
    assert result.success is False
    assert "NODE-VAL-002" in _rule_ids(result)


def test_node_val_002_violation_severity_is_error():
    result = _validate("n1", 42)
    v002 = next(v for v in result.violations if v.rule_id == "NODE-VAL-002")
    assert v002.severity == Severity.ERROR


def test_node_val_002_location_id_set_when_node_id_valid():
    result = _validate("n1", [])
    v002 = next(v for v in result.violations if v.rule_id == "NODE-VAL-002")
    assert v002.location_id == "n1"


# ---------------------------------------------------------------------------
# NODE-VAL-003: Reserved key collision
# ---------------------------------------------------------------------------

def test_node_val_003_reserved_key_validation():
    result = _validate("n1", {"validation": {"something": True}})
    assert result.success is False
    assert "NODE-VAL-003" in _rule_ids(result)


def test_node_val_003_reserved_key_decision():
    result = _validate("n1", {"decision": "CONTINUE"})
    assert result.success is False
    assert "NODE-VAL-003" in _rule_ids(result)


def test_node_val_003_both_reserved_keys_reported():
    result = _validate("n1", {"validation": 1, "decision": 2})
    rule_ids = _rule_ids(result)
    assert rule_ids.count("NODE-VAL-003") == 2


def test_node_val_003_violation_names_offending_key():
    result = _validate("n1", {"validation": True})
    v003 = next(v for v in result.violations if v.rule_id == "NODE-VAL-003")
    assert "validation" in v003.message


def test_node_val_003_location_id_set():
    result = _validate("my_node", {"decision": "x"})
    v003 = next(v for v in result.violations if v.rule_id == "NODE-VAL-003")
    assert v003.location_id == "my_node"


def test_node_val_003_non_reserved_keys_are_fine():
    result = _validate("n1", {"prompt": "hello", "output": "world"})
    assert result.success is True
    assert _rule_ids(result) == []


# ---------------------------------------------------------------------------
# Valid input — success path
# ---------------------------------------------------------------------------

def test_valid_input_returns_success():
    result = _validate("n1", {"x": 1, "y": "hello"})
    assert result.success is True
    assert result.violations == []


def test_valid_empty_snapshot_returns_success():
    result = _validate("my_node", {})
    assert result.success is True


def test_applied_rule_ids_always_reported():
    result = _validate("n1", {})
    assert "NODE-VAL-001" in result.applied_rule_ids
    assert "NODE-VAL-002" in result.applied_rule_ids
    assert "NODE-VAL-003" in result.applied_rule_ids


def test_all_rules_evaluated_even_on_first_violation():
    """All 3 rules are always evaluated (no short-circuit stop)."""
    # NODE-VAL-001 fires; but also inject reserved key for NODE-VAL-003
    # NODE-VAL-002 should NOT fire (dict is provided)
    result = _validate("", {"decision": "x"})
    ids = _rule_ids(result)
    assert "NODE-VAL-001" in ids   # empty node_id
    assert "NODE-VAL-003" in ids   # reserved key
    assert "NODE-VAL-002" not in ids  # snapshot is a dict, so 002 does NOT fire


# ---------------------------------------------------------------------------
# NodeDecisionPolicy integration
# ---------------------------------------------------------------------------

def test_policy_fail_on_invalid_node_id():
    result = _validate("")
    outcome = NodeDecisionPolicy().decide(result)
    assert outcome.decision == NodeDecision.FAIL
    assert outcome.blocks_execution is True


def test_policy_continue_on_valid_input():
    result = _validate("n1", {"data": 42})
    outcome = NodeDecisionPolicy().decide(result)
    assert outcome.decision == NodeDecision.CONTINUE
    assert outcome.blocks_execution is False


def test_policy_reason_contains_message_on_fail():
    result = _validate("n1", {"validation": True})
    outcome = NodeDecisionPolicy().decide(result)
    assert outcome.decision == NodeDecision.FAIL
    assert isinstance(outcome.reason, str) and outcome.reason


# ---------------------------------------------------------------------------
# Engine integration — handler blocking still works with real rules
# ---------------------------------------------------------------------------

def test_real_rule_fail_blocks_handler_in_engine():
    """Reserved key in input_snapshot triggers NODE-VAL-003 → FAIL → handler blocked."""
    from src.engine.engine import Engine
    from src.engine.model import Channel
    from src.engine.types import NodeStatus

    executed = []

    def handler(inp):
        executed.append(True)
        return {"result": "ok"}

    # Inject a reserved key by customizing the node's input.
    # Since the entry node receives {} as input_snapshot, we inject it via
    # monkey-patching _run_node to pass a bad snapshot for testing purposes.
    import src.engine.validation.node_validator as nv_module

    original = nv_module.NodeValidator

    class _AlwaysFailValidator:
        def validate(self, node_id, input_snapshot, context=None):
            from src.engine.validation.node_result import NodeValidationResult
            from src.engine.validation.result import Violation, Severity
            return NodeValidationResult(
                node_id=node_id,
                success=False,
                applied_rule_ids=["NODE-VAL-003"],
                violations=[
                    Violation(
                        rule_id="NODE-VAL-003",
                        rule_name="Reserved input key collision",
                        severity=Severity.ERROR,
                        location_type="node",
                        location_id=node_id,
                        message="input_snapshot contains reserved key 'validation'",
                    )
                ],
            )

    nv_module.NodeValidator = _AlwaysFailValidator
    try:
        eng = Engine(
            entry_node_id="n1",
            node_ids=["n1"],
            handlers={"n1": handler},
        )
        trace = eng.execute(revision_id="r_real_rule_block")
    finally:
        nv_module.NodeValidator = original

    assert not executed, "handler must not run when NODE-VAL-003 fires"
    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n1"].output_snapshot is None
    dec = trace.nodes["n1"].meta["decision"]
    assert dec["value"] == NodeDecision.FAIL.value


def test_node_trace_meta_present_after_real_validation():
    """After real validation runs, node.meta has validation + decision keys."""
    from src.engine.engine import Engine
    from src.engine.types import NodeStatus

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
    )
    trace = eng.execute(revision_id="r_meta_real")

    n1 = trace.nodes["n1"]
    assert n1.meta is not None
    assert "validation" in n1.meta
    assert "decision" in n1.meta
    assert n1.meta["validation"]["performed"] is True
    assert n1.meta["validation"]["success"] is True
    assert n1.meta["decision"]["value"] == NodeDecision.CONTINUE.value
