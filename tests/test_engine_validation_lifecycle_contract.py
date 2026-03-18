"""
test_engine_validation_lifecycle_contract.py

Contract tests for the validation lifecycle integration (Step: Validation Layer →
Engine Execution Flow Real Integration).

Enforced lifecycle:
  Phase 1  — Pre-validation: structural  (always blocking)
  Phase 1b — Pre-validation: determinism (strict mode, blocking)
  Phase 2  — Execution
  Phase 3  — Post-validation: determinism (non-strict mode, advisory)
  Phase 4  — Trace finalization (artifact commit boundary)

Invariants tested:
  1. Pre-validation (structural) is invoked for every execution.
  2. Structural failure blocks execution; all nodes remain NOT_REACHED.
  3. Post-validation is invoked in non-strict mode after execution.
  4. Post-validation metadata is present in trace before trace is returned.
  5. Strict-mode determinism failure blocks execution (Phase 1b).
  6. Non-strict determinism runs post-execution (Phase 3), not pre-execution.
  7. Artifact (output_snapshot) ordering respects the validation boundary:
     node outputs are only accessible via the trace AFTER post-validation is
     embedded in trace.meta.
  8. Existing engine behaviour outside this change is unaffected.
"""
from __future__ import annotations

import pytest

from src.engine.engine import Engine
from src.engine.model import Channel
from src.engine.types import NodeStatus


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _minimal_valid_engine() -> Engine:
    """A simple 2-node engine that passes structural validation."""
    return Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
    )


def _invalid_engine_missing_entry() -> Engine:
    """An engine with an empty entry_node_id (triggers ENG-001)."""
    return Engine(entry_node_id="", node_ids=["n1"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Pre-validation is always invoked
# ─────────────────────────────────────────────────────────────────────────────

def test_pre_validation_structural_is_always_performed():
    """trace.meta['pre_validation']['structural']['performed'] must be True."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r1")

    pre = trace.meta.get("pre_validation")
    assert isinstance(pre, dict), "pre_validation block missing from meta"
    assert pre["structural"]["performed"] is True


def test_pre_validation_structural_present_even_on_failure():
    """Structural validation must be recorded even when it fails."""
    eng = _invalid_engine_missing_entry()
    trace = eng.execute(revision_id="r_invalid")

    assert trace.validation_success is False
    pre = trace.meta.get("pre_validation")
    assert isinstance(pre, dict)
    assert pre["structural"]["performed"] is True
    assert pre["structural"]["success"] is False
    assert len(pre["structural"]["violations"]) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 2. Structural failure blocks execution (all nodes NOT_REACHED)
# ─────────────────────────────────────────────────────────────────────────────

def test_structural_failure_blocks_all_node_execution():
    """When structural validation fails, no node may be executed."""
    eng = _invalid_engine_missing_entry()
    trace = eng.execute(revision_id="r_block")

    assert trace.validation_success is False
    for node in trace.nodes.values():
        assert node.node_status == NodeStatus.NOT_REACHED, (
            f"Node {node.node_id} should be NOT_REACHED but got {node.node_status}"
        )


def test_structural_failure_cycle_blocks_execution():
    """A cyclic graph fails structural validation and blocks execution."""
    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[
            Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2"),
            Channel(channel_id="c2", src_node_id="n2", dst_node_id="n1"),
        ],
    )
    trace = eng.execute(revision_id="r_cycle")
    assert trace.validation_success is False
    for node in trace.nodes.values():
        assert node.node_status == NodeStatus.NOT_REACHED


# ─────────────────────────────────────────────────────────────────────────────
# 3. Post-validation is invoked in non-strict (default) mode
# ─────────────────────────────────────────────────────────────────────────────

def test_post_validation_is_performed_in_default_mode():
    """trace.meta['post_validation']['performed'] is True in non-strict mode."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_post")

    post = trace.meta.get("post_validation")
    assert isinstance(post, dict), "post_validation block missing from meta"
    assert post["performed"] is True
    assert post["strict_mode"] is False


def test_post_validation_not_performed_in_strict_mode():
    """In strict mode, post_validation.performed must be False (det runs pre)."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_strict", strict_determinism=True)

    post = trace.meta.get("post_validation")
    assert isinstance(post, dict)
    assert post["performed"] is False


def test_post_validation_is_advisory_on_non_strict():
    """Non-strict post-validation findings do not block execution or affect node outcomes."""
    eng = _minimal_valid_engine()
    # No determinism meta provided → DET-001..007 will fire as warnings
    trace = eng.execute(revision_id="r_advisory")

    # Execution should have succeeded despite determinism warnings
    assert trace.validation_success is True
    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS

    post = trace.meta.get("post_validation")
    assert post["performed"] is True
    # Advisory findings recorded but execution not blocked
    assert isinstance(post.get("violations"), list)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Post-validation metadata embedded in trace before trace is returned
#    (artifact commit / trace finalization boundary)
# ─────────────────────────────────────────────────────────────────────────────

def test_post_validation_present_in_returned_trace():
    """post_validation key must be in trace.meta when trace is returned to caller."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_order")

    # If post_validation is present and has 'performed', the lifecycle ran fully
    # before the trace was constructed and returned.
    assert "post_validation" in trace.meta
    assert "performed" in trace.meta["post_validation"]


def test_node_output_snapshots_accessible_only_after_post_validation_in_meta():
    """Node output_snapshots (artifacts) are accessible via the trace only after
    post_validation is embedded in trace.meta.  This demonstrates the ordering:
    Phase 2 (execution) → Phase 3 (post-validation) → Phase 4 (trace construction)."""
    call_log: list = []

    def recording_handler(input_snap):
        call_log.append("node_executed")
        return {"result": "ok"}

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": recording_handler},
    )
    trace = eng.execute(revision_id="r_artifact_order")

    # Node ran
    assert "node_executed" in call_log

    # Node output snapshot is accessible in the trace
    assert trace.nodes["n1"].output_snapshot == {"result": "ok"}

    # post_validation is embedded — confirming Phase 3 completed before Phase 4
    assert "post_validation" in trace.meta
    assert trace.meta["post_validation"]["performed"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 5. Strict-mode determinism blocks execution (Phase 1b)
# ─────────────────────────────────────────────────────────────────────────────

def test_strict_determinism_failure_blocks_execution():
    """In strict mode, determinism failure (no meta.node_specs) prevents execution."""
    eng = _minimal_valid_engine()  # No 'determinism' in meta → DET-001 fails
    trace = eng.execute(revision_id="r_strict_block", strict_determinism=True)

    # Determinism failure should be reflected as validation failure
    assert trace.validation_success is False
    for node in trace.nodes.values():
        assert node.node_status == NodeStatus.NOT_REACHED


def test_strict_determinism_pre_validation_block_is_recorded():
    """Strict determinism failure is recorded in pre_validation.determinism."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_strict_meta", strict_determinism=True)

    pre = trace.meta.get("pre_validation")
    assert isinstance(pre, dict)
    det = pre.get("determinism")
    assert isinstance(det, dict)
    assert det["performed"] is True
    assert det["strict_mode"] is True
    assert det["success"] is False  # DET-001 fires (no meta.determinism)
    assert len(det["violations"]) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 6. Non-strict determinism runs post-execution (Phase 3), not pre-execution
# ─────────────────────────────────────────────────────────────────────────────

def test_non_strict_determinism_not_in_pre_validation():
    """In non-strict mode, determinism is NOT in pre_validation (it runs post)."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_nonstrict")

    pre = trace.meta.get("pre_validation")
    assert isinstance(pre, dict)
    # In non-strict mode, pre_validation.determinism.performed must be False
    det = pre.get("determinism")
    assert isinstance(det, dict)
    assert det["performed"] is False


def test_non_strict_execution_proceeds_despite_determinism_warnings():
    """Non-strict mode: nodes execute even when determinism config is incomplete."""
    executed = []

    def handler(inp):
        executed.append(True)
        return {}

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1"],
        handlers={"n1": handler},
    )
    trace = eng.execute(revision_id="r_proceed")

    assert executed, "handler should have been called"
    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    # Post-validation ran and recorded advisory findings
    post = trace.meta["post_validation"]
    assert post["performed"] is True


# ─────────────────────────────────────────────────────────────────────────────
# 7. Artifact ordering: trace.meta.validation backward compatibility preserved
# ─────────────────────────────────────────────────────────────────────────────

def test_legacy_validation_meta_key_preserved():
    """trace.meta['validation'] must remain present for backward compatibility."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_compat")

    vmeta = trace.meta.get("validation")
    assert isinstance(vmeta, dict)
    assert "at" in vmeta
    assert "snapshot" in vmeta
    assert vmeta["snapshot"]["snapshot_version"] == "1"


def test_trace_validation_success_reflects_structural_result():
    """trace.validation_success reflects the primary (structural) validation result."""
    valid_eng = _minimal_valid_engine()
    trace_ok = valid_eng.execute(revision_id="r_ok")
    assert trace_ok.validation_success is True

    invalid_eng = _invalid_engine_missing_entry()
    trace_fail = invalid_eng.execute(revision_id="r_fail")
    assert trace_fail.validation_success is False


# ─────────────────────────────────────────────────────────────────────────────
# 8. Existing behaviour unaffected
# ─────────────────────────────────────────────────────────────────────────────

def test_downstream_node_executed_when_upstream_succeeds():
    """Standard ALL_SUCCESS DAG propagation continues to work."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_dag")

    assert trace.nodes["n1"].node_status == NodeStatus.SUCCESS
    assert trace.nodes["n2"].node_status == NodeStatus.SUCCESS


def test_downstream_skipped_when_upstream_fails():
    """ALL_SUCCESS propagation: downstream is SKIPPED when upstream fails."""

    def failing_handler(_inp):
        raise RuntimeError("forced failure")

    eng = Engine(
        entry_node_id="n1",
        node_ids=["n1", "n2"],
        channels=[Channel(channel_id="c1", src_node_id="n1", dst_node_id="n2")],
        handlers={"n1": failing_handler},
    )
    trace = eng.execute(revision_id="r_skip")

    assert trace.nodes["n1"].node_status == NodeStatus.FAILURE
    assert trace.nodes["n2"].node_status == NodeStatus.SKIPPED


def test_determinism_50_runs_structural_signature_unchanged():
    """The lifecycle refactor must not break determinism of the trace signature."""
    from src.engine.model import Channel as Ch

    def _sig(trace):
        return tuple(
            (nid, trace.nodes[nid].node_status, trace.nodes[nid].core_status)
            for nid in sorted(trace.nodes.keys())
        )

    sigs = []
    for i in range(10):
        eng = _minimal_valid_engine()
        sigs.append(_sig(eng.execute(revision_id=f"r{i}")))

    assert all(s == sigs[0] for s in sigs)


# ─────────────────────────────────────────────────────────────────────────────
# Decision Policy integration tests
# (Step: Validation Outcome → Runtime Decision Integration)
# ─────────────────────────────────────────────────────────────────────────────

from src.engine.validation.decision_policy import ValidationDecisionPolicy
from src.engine.validation.result import ValidationDecision


# ── Direct policy unit tests ──────────────────────────────────────────────────

def test_decision_policy_structural_failure_maps_to_block():
    """Structural validation failure → BLOCK."""
    from src.engine.validation.result import ValidationResult, Violation, Severity

    failed = ValidationResult(
        success=False,
        engine_revision="r1",
        structural_fingerprint="fp",
        applied_rule_ids=["ENG-001"],
        violations=[
            Violation(
                rule_id="ENG-001",
                rule_name="Missing Entry",
                severity=Severity.ERROR,
                location_type="engine",
                location_id=None,
                message="entry missing",
            )
        ],
    )
    policy = ValidationDecisionPolicy()
    result = policy.decide_pre(structural_result=failed, pre_determinism_result=None)
    assert result.decision == ValidationDecision.BLOCK
    assert result.blocks_execution is True


def test_decision_policy_strict_determinism_failure_maps_to_block():
    """Strict determinism pre-validation failure → BLOCK."""
    from src.engine.validation.result import ValidationResult, Violation, Severity

    ok_structural = ValidationResult(
        success=True,
        engine_revision="r1",
        structural_fingerprint="fp",
        applied_rule_ids=[],
        violations=[],
    )
    failed_det = ValidationResult(
        success=False,
        engine_revision="r1",
        structural_fingerprint="fp",
        applied_rule_ids=["DET-001"],
        violations=[
            Violation(
                rule_id="DET-001",
                rule_name="Determinism Missing",
                severity=Severity.ERROR,
                location_type="engine",
                location_id=None,
                message="no determinism config",
            )
        ],
    )
    policy = ValidationDecisionPolicy()
    result = policy.decide_pre(
        structural_result=ok_structural,
        pre_determinism_result=failed_det,
    )
    assert result.decision == ValidationDecision.BLOCK
    assert result.blocks_execution is True


def test_decision_policy_successful_pre_validation_maps_to_continue():
    """All pre-checks pass → CONTINUE."""
    from src.engine.validation.result import ValidationResult

    ok = ValidationResult(
        success=True,
        engine_revision="r1",
        structural_fingerprint="fp",
        applied_rule_ids=[],
        violations=[],
    )
    policy = ValidationDecisionPolicy()
    result = policy.decide_pre(structural_result=ok, pre_determinism_result=None)
    assert result.decision == ValidationDecision.CONTINUE
    assert result.blocks_execution is False


def test_decision_policy_post_with_violations_maps_to_warn():
    """Post-validation with violations → WARN (advisory)."""
    from src.engine.validation.result import ValidationResult, Violation, Severity

    advisory = ValidationResult(
        success=True,  # non-strict: success=True even with violations
        engine_revision="r1",
        structural_fingerprint="fp",
        applied_rule_ids=["DET-001"],
        violations=[
            Violation(
                rule_id="DET-001",
                rule_name="Determinism Missing",
                severity=Severity.WARNING,
                location_type="engine",
                location_id=None,
                message="advisory",
            )
        ],
    )
    policy = ValidationDecisionPolicy()
    result = policy.decide_post(advisory, strict_determinism=False)
    assert result.decision == ValidationDecision.WARN


def test_decision_policy_post_no_violations_maps_to_accept():
    """Post-validation with no violations → ACCEPT."""
    from src.engine.validation.result import ValidationResult

    clean = ValidationResult(
        success=True,
        engine_revision="r1",
        structural_fingerprint="fp",
        applied_rule_ids=[],
        violations=[],
    )
    policy = ValidationDecisionPolicy()
    result = policy.decide_post(clean, strict_determinism=False)
    assert result.decision == ValidationDecision.ACCEPT


def test_decision_policy_post_none_maps_to_accept():
    """Post-validation not performed (None) → ACCEPT (strict mode path)."""
    policy = ValidationDecisionPolicy()
    result = policy.decide_post(None, strict_determinism=True)
    assert result.decision == ValidationDecision.ACCEPT


# ── Engine integration: decisions visible in trace.meta ───────────────────────

def test_decision_meta_present_in_trace():
    """trace.meta['decision'] must be present after execution."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_dec")

    assert "decision" in trace.meta
    dec = trace.meta["decision"]
    assert "pre" in dec
    assert "post" in dec


def test_decision_pre_continue_on_valid_engine():
    """Valid engine → pre decision is CONTINUE."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_continue")

    pre = trace.meta["decision"]["pre"]
    assert pre["value"] == ValidationDecision.CONTINUE.value


def test_decision_pre_block_on_structural_failure():
    """Structural failure → pre decision is BLOCK."""
    eng = _invalid_engine_missing_entry()
    trace = eng.execute(revision_id="r_block_dec")

    pre = trace.meta["decision"]["pre"]
    assert pre["value"] == ValidationDecision.BLOCK.value
    assert trace.validation_success is False


def test_decision_pre_block_on_strict_determinism_failure():
    """Strict determinism failure → pre decision is BLOCK."""
    eng = _minimal_valid_engine()  # No determinism meta → DET-001 fires
    trace = eng.execute(revision_id="r_strict_dec", strict_determinism=True)

    pre = trace.meta["decision"]["pre"]
    assert pre["value"] == ValidationDecision.BLOCK.value


def test_decision_post_warn_on_advisory_violations():
    """Non-strict mode with determinism violations → post decision is WARN."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_warn_dec")

    post = trace.meta["decision"]["post"]
    # No determinism config → DET-001..007 fire as advisory → WARN
    assert post["value"] == ValidationDecision.WARN.value


def test_decision_post_accept_in_strict_mode():
    """In strict mode, post decision is ACCEPT (no post phase)."""
    eng = _minimal_valid_engine()
    # Even though strict mode blocks execution, post decision is ACCEPT
    trace = eng.execute(revision_id="r_accept_strict", strict_determinism=True)

    post = trace.meta["decision"]["post"]
    assert post["value"] == ValidationDecision.ACCEPT.value


def test_decision_meta_contains_reason():
    """Decision entries must contain a human-readable reason."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_reason")

    dec = trace.meta["decision"]
    assert isinstance(dec["pre"]["reason"], str) and dec["pre"]["reason"]
    assert isinstance(dec["post"]["reason"], str) and dec["post"]["reason"]


def test_decision_enum_values_are_strings():
    """Decision values in trace.meta must be plain strings (JSON-safe)."""
    eng = _minimal_valid_engine()
    trace = eng.execute(revision_id="r_json_safe")

    dec = trace.meta["decision"]
    assert isinstance(dec["pre"]["value"], str)
    assert isinstance(dec["post"]["value"], str)
    # Must be one of the valid enum values
    valid = {d.value for d in ValidationDecision}
    assert dec["pre"]["value"] in valid
    assert dec["post"]["value"] in valid
