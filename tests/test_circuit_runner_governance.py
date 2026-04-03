"""
test_circuit_runner_governance.py

Tests for CircuitRunner governance lifecycle and the migration of Engine governance
to EngineGovernanceOrchestrator.
"""
from __future__ import annotations
import pytest
from src.circuit.circuit_runner import (
    CircuitRunner, CircuitGovernanceTrace, CircuitRunResult,
)
from src.engine.validation.result import ValidationDecision
from src.engine.validation.governance_orchestrator import EngineGovernanceOrchestrator


# ── Test fixtures ─────────────────────────────────────────────────────────────

class _SimpleRegistry:
    def __init__(self, configs=None):
        self._configs = configs or {}
    def get(self, config_id):
        return self._configs.get(config_id)
    def register(self, config):
        self._configs[config["config_id"]] = config

class _SimpleRuntime:
    def __init__(self, outputs=None):
        self._outputs = outputs or {}
        self.executed = []
    def execute_by_config_id(self, registry, config_id, state):
        self.executed.append(config_id)
        class R:
            def __init__(self, o): self.output = o
        return R(self._outputs.get(config_id, f"out:{config_id}"))

def _reg():
    r = _SimpleRegistry()
    r.register({"config_id": "cfg.a"})
    return r

def _valid_circuit():
    return {"id": "tc", "nodes": [{"id": "n_a", "execution_config_ref": "cfg.a"}]}


# ── Test 1: Structural pre-validation blocks execution ───────────────────────

def test_structural_block_duplicate_node():
    rt = _SimpleRuntime()
    runner = CircuitRunner(rt, _reg())
    circuit = {"nodes": [
        {"id": "n_a", "execution_config_ref": "cfg.a"},
        {"id": "n_a", "execution_config_ref": "cfg.a"},
    ]}
    result = runner.execute(circuit, {})
    assert rt.executed == []
    gov = result.governance
    assert gov.structural_success is False
    assert gov.pre_decision == ValidationDecision.BLOCK.value
    assert gov.execution_allowed is False
    assert gov.final_status == "blocked"


def test_structural_block_missing_dep():
    rt = _SimpleRuntime()
    runner = CircuitRunner(rt, _reg())
    circuit = {"nodes": [{"id": "n_a", "execution_config_ref": "cfg.a", "depends_on": ["ghost"]}]}
    result = runner.execute(circuit, {})
    assert rt.executed == []
    assert result.governance.pre_decision == ValidationDecision.BLOCK.value


def test_structural_block_cycle():
    r = _SimpleRegistry()
    r.register({"config_id": "cfg.a"})
    r.register({"config_id": "cfg.b"})
    rt = _SimpleRuntime()
    runner = CircuitRunner(rt, r)
    circuit = {"nodes": [
        {"id": "a", "execution_config_ref": "cfg.a", "depends_on": ["b"]},
        {"id": "b", "execution_config_ref": "cfg.b", "depends_on": ["a"]},
    ]}
    result = runner.execute(circuit, {})
    assert rt.executed == []
    assert result.governance.pre_decision == ValidationDecision.BLOCK.value


def test_structural_valid_circuit_proceeds():
    rt = _SimpleRuntime({"cfg.a": "ok"})
    runner = CircuitRunner(rt, _reg())
    result = runner.execute(_valid_circuit(), {})
    assert result.governance.structural_success is True
    assert result.governance.pre_decision == ValidationDecision.CONTINUE.value
    assert result.governance.execution_allowed is True
    assert result["n_a"] == "ok"


# ── Test 2: Strict determinism block ─────────────────────────────────────────

def test_strict_determinism_pre_check_performed():
    """
    strict_determinism=True triggers the Phase 1b pre-check.
    No circuit-level det rules yet, so this still passes — but the hook IS wired.
    """
    rt = _SimpleRuntime({"cfg.a": "ok"})
    runner = CircuitRunner(rt, _reg())
    result = runner.execute(_valid_circuit(), {}, strict_determinism=True)
    gov = result.governance
    assert gov.determinism_pre_performed is True
    assert gov.pre_decision == ValidationDecision.CONTINUE.value  # no violations yet
    # In strict mode, post-validation is NOT performed (same contract as Engine)
    assert gov.determinism_post_performed is False


def test_non_strict_post_check_performed():
    """Non-strict: determinism post-check runs AFTER execution (advisory)."""
    rt = _SimpleRuntime({"cfg.a": "ok"})
    runner = CircuitRunner(rt, _reg())
    result = runner.execute(_valid_circuit(), {})
    gov = result.governance
    assert gov.determinism_pre_performed is False
    assert gov.determinism_post_performed is True
    assert gov.post_decision in (ValidationDecision.ACCEPT.value, ValidationDecision.WARN.value)


# ── Test 3: Pre-decision block stops execution ────────────────────────────────

def test_pre_decision_block_stops_node_execution():
    rt = _SimpleRuntime()
    runner = CircuitRunner(rt, _SimpleRegistry())
    circuit = {"nodes": [{"id": "a", "execution_config_ref": "cfg.a", "depends_on": ["missing"]}]}
    result = runner.execute(circuit, {})
    assert rt.executed == []
    assert result.governance.execution_completed is False
    assert result.governance.pre_decision == ValidationDecision.BLOCK.value


# ── Test 4: Post-decision advisory in final governance ────────────────────────

def test_post_decision_present_in_governance():
    rt = _SimpleRuntime({"cfg.a": "ok"})
    runner = CircuitRunner(rt, _reg())
    result = runner.execute(_valid_circuit(), {})
    gov = result.governance
    assert gov.post_decision in (ValidationDecision.ACCEPT.value, ValidationDecision.WARN.value)
    assert gov.post_decision_reason != ""
    assert gov.execution_completed is True


# ── Test 5: Final trace finalization with required fields ─────────────────────

def test_final_governance_trace_required_fields():
    rt = _SimpleRuntime({"cfg.a": "ok"})
    runner = CircuitRunner(rt, _reg())
    result = runner.execute(_valid_circuit(), {"k": "v"})
    gov = result.governance
    assert isinstance(gov, CircuitGovernanceTrace)
    assert gov.execution_id and len(gov.execution_id) > 0
    assert gov.started_at_ms > 0
    assert gov.finished_at_ms is not None
    assert gov.duration_ms is not None and gov.duration_ms >= 0
    assert gov.final_status in ("success", "blocked", "failed", "paused")
    assert gov.pre_decision in [d.value for d in ValidationDecision]
    assert gov.post_decision in [d.value for d in ValidationDecision]
    assert isinstance(gov.structural_violations, list)


def test_blocked_trace_still_finalized():
    rt = _SimpleRuntime()
    runner = CircuitRunner(rt, _SimpleRegistry())
    circuit = {"nodes": [{"id": "a", "execution_config_ref": "cfg.a", "depends_on": ["x"]}]}
    result = runner.execute(circuit, {})
    gov = result.governance
    assert gov.execution_id and len(gov.execution_id) > 0
    assert gov.finished_at_ms is not None
    assert gov.duration_ms is not None
    assert gov.final_status == "blocked"


def test_governance_to_dict_has_expected_keys():
    rt = _SimpleRuntime({"cfg.a": "ok"})
    runner = CircuitRunner(rt, _reg())
    result = runner.execute(_valid_circuit(), {})
    d = result.governance.to_dict()
    for key in ("execution_id", "pre_validation", "pre_decision",
                 "post_validation", "post_decision", "final_status", "timing"):
        assert key in d, f"missing key: {key}"


# ── Test 6: No-double-application regression ──────────────────────────────────

def test_circuit_runner_does_not_call_engine_governance_orchestrator():
    """
    CircuitRunner uses its own validation chain.
    EngineGovernanceOrchestrator must NOT be instantiated during circuit path.
    """
    original_init = EngineGovernanceOrchestrator.__init__
    calls = []
    def tracking_init(self):
        calls.append(1)
        original_init(self)
    EngineGovernanceOrchestrator.__init__ = tracking_init
    try:
        rt = _SimpleRuntime({"cfg.a": "ok"})
        runner = CircuitRunner(rt, _reg())
        runner.execute(_valid_circuit(), {})
    finally:
        EngineGovernanceOrchestrator.__init__ = original_init
    assert len(calls) == 0, (
        f"EngineGovernanceOrchestrator instantiated {len(calls)} times in CircuitRunner path"
    )


def test_decision_policy_called_once_in_circuit_runner():
    """ValidationDecisionPolicy.decide_pre/post called exactly once per execute()."""
    from src.engine.validation.decision_policy import ValidationDecisionPolicy
    counts = {"pre": 0, "post": 0}
    orig_pre = ValidationDecisionPolicy.decide_pre
    orig_post = ValidationDecisionPolicy.decide_post
    def track_pre(self, *a, **kw):
        counts["pre"] += 1
        return orig_pre(self, *a, **kw)
    def track_post(self, *a, **kw):
        counts["post"] += 1
        return orig_post(self, *a, **kw)
    ValidationDecisionPolicy.decide_pre = track_pre
    ValidationDecisionPolicy.decide_post = track_post
    try:
        rt = _SimpleRuntime({"cfg.a": "ok"})
        runner = CircuitRunner(rt, _reg())
        runner.execute(_valid_circuit(), {})
    finally:
        ValidationDecisionPolicy.decide_pre = orig_pre
        ValidationDecisionPolicy.decide_post = orig_post
    assert counts["pre"] == 1
    assert counts["post"] == 1


# ── Test 7: Engine/CircuitRunner consistency ──────────────────────────────────

def test_engine_governance_delegated_to_orchestrator():
    """
    Engine.execute() now delegates to EngineGovernanceOrchestrator.
    EngineGovernanceOrchestrator.run_pre is called during engine.execute().
    """
    from src.engine.engine import Engine
    original_run_pre = EngineGovernanceOrchestrator.run_pre
    calls = []
    def tracking_run_pre(self, *a, **kw):
        calls.append(1)
        return original_run_pre(self, *a, **kw)
    EngineGovernanceOrchestrator.run_pre = tracking_run_pre
    try:
        engine = Engine(
            entry_node_id="n1",
            node_ids=["n1"],
            handlers={"n1": lambda s: {"ok": True}},
        )
        engine.execute(revision_id="r1")
    finally:
        EngineGovernanceOrchestrator.run_pre = original_run_pre
    assert len(calls) == 1, (
        f"EngineGovernanceOrchestrator.run_pre called {len(calls)} times, expected 1"
    )


def test_both_paths_block_on_structural_failure_same_decision():
    """
    Both Engine path and CircuitRunner path produce BLOCK for structural failure.
    Same governance contract, different validators, same decision policy.
    """
    from src.engine.engine import Engine
    from src.engine.validation.validator import ValidationEngine
    from src.engine.validation.decision_policy import ValidationDecisionPolicy

    # Engine path: NODE-001 (duplicate node_ids)
    engine = Engine(entry_node_id="a", node_ids=["a", "a"])
    validator = ValidationEngine()
    policy = ValidationDecisionPolicy()
    eng_structural = validator.validate_structural(engine, revision_id="test")
    eng_pre_decision = policy.decide_pre(eng_structural, None)
    assert eng_pre_decision.decision == ValidationDecision.BLOCK

    # CircuitRunner path: CIRCUIT-STRUCTURAL (duplicate node IDs)
    rt = _SimpleRuntime()
    r = _SimpleRegistry()
    r.register({"config_id": "cfg.a"})
    runner = CircuitRunner(rt, r)
    circuit = {"nodes": [
        {"id": "a", "execution_config_ref": "cfg.a"},
        {"id": "a", "execution_config_ref": "cfg.a"},
    ]}
    result = runner.execute(circuit, {})
    assert result.governance.pre_decision == ValidationDecision.BLOCK.value

    # Both paths: same outcome (BLOCK), consistent contract


def test_circuit_run_result_is_backward_compat_dict():
    """result["node_id"] works. governance is NOT a dict key."""
    rt = _SimpleRuntime({"cfg.a": "out-a"})
    runner = CircuitRunner(rt, _reg())
    result = runner.execute(_valid_circuit(), {"init": "v"})
    assert result["n_a"] == "out-a"
    assert result["init"] == "v"
    assert isinstance(result, dict)
    assert "governance" not in dict.keys(result)
    assert isinstance(result.governance, CircuitGovernanceTrace)


# ── Engine.execute() delegation proof ─────────────────────────────────────────

def test_engine_execute_delegates_to_orchestrator_not_inline():
    """
    Engine.execute() must delegate governance to EngineGovernanceOrchestrator.

    Proven by patching EngineGovernanceOrchestrator.run_pre: if Engine.execute()
    delegates, it MUST call run_pre exactly once. If Engine owned governance inline
    it would bypass run_pre entirely.
    """
    run_pre_calls = []
    original_run_pre = EngineGovernanceOrchestrator.run_pre

    def tracking_run_pre(self, engine_obj, *, revision_id, strict_determinism):
        run_pre_calls.append({"revision_id": revision_id, "strict": strict_determinism})
        return original_run_pre(self, engine_obj, revision_id=revision_id,
                                strict_determinism=strict_determinism)

    EngineGovernanceOrchestrator.run_pre = tracking_run_pre
    try:
        from src.engine.engine import Engine
        engine = Engine(
            entry_node_id="n1",
            node_ids=["n1"],
            handlers={"n1": lambda s: {"ok": True}},
        )
        engine.execute(revision_id="r_delegate_proof")
    finally:
        EngineGovernanceOrchestrator.run_pre = original_run_pre

    assert len(run_pre_calls) == 1, (
        f"run_pre called {len(run_pre_calls)} times — expected 1. "
        "Engine must delegate governance rather than owning it inline."
    )
    assert run_pre_calls[0]["revision_id"] == "r_delegate_proof"


def test_resume_request_emits_execution_resumed_and_skips_completed_nodes():
    r = _SimpleRegistry()
    r.register({"config_id": "cfg.a"})
    r.register({"config_id": "cfg.b"})
    r.register({"config_id": "cfg.c"})

    class _EventRuntime(_SimpleRuntime):
        def __init__(self, outputs=None):
            super().__init__(outputs)
            self.events = []
        def _emit_event(self, event_type, payload, node_id=None):
            self.events.append((event_type, payload, node_id))

    rt = _EventRuntime({"cfg.b": "out:b", "cfg.c": "out:c"})
    runner = CircuitRunner(rt, r)
    circuit = {
        "id": "tc-resume",
        "nodes": [
            {"id": "a", "execution_config_ref": "cfg.a"},
            {"id": "b", "execution_config_ref": "cfg.b", "depends_on": ["a"]},
            {"id": "c", "execution_config_ref": "cfg.c", "depends_on": ["b"]},
        ],
    }
    state = {
        "__node_outputs__": {"a": "out:a"},
        "__resume__": {
            "resume_from_node_id": "b",
            "previous_execution_id": "exec-paused-1",
        },
    }

    result = runner.execute(circuit, state)

    assert rt.executed == ["cfg.b", "cfg.c"]
    assert result["b"] == "out:b"
    assert result["c"] == "out:c"
    assert [event[0] for event in rt.events[:2]] == ["execution_started", "execution_resumed"]
    assert rt.events[0][1]["is_resume"] is True
    assert rt.events[1][1]["previous_execution_id"] == "exec-paused-1"


def test_resume_request_requires_completed_dependency_outputs():
    r = _SimpleRegistry()
    r.register({"config_id": "cfg.a"})
    r.register({"config_id": "cfg.b"})
    rt = _SimpleRuntime({"cfg.b": "out:b"})
    runner = CircuitRunner(rt, r)
    circuit = {
        "id": "tc-resume-invalid",
        "nodes": [
            {"id": "a", "execution_config_ref": "cfg.a"},
            {"id": "b", "execution_config_ref": "cfg.b", "depends_on": ["a"]},
        ],
    }
    state = {
        "__node_outputs__": {},
        "__resume__": {"resume_from_node_id": "b"},
    }

    with pytest.raises(ValueError, match="resume execution requires completed dependency outputs"):
        runner.execute(circuit, state)
