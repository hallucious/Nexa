"""
test_paused_run_state.py

Focused tests for the persisted pause-state / resume-token foundation.

Covers:
  1. persisted pause state does not fake completion
  2. resumable boundary is deterministic-safe (frozenset, immutable)
  3. stale/invalid paused state is rejected explicitly
  4. resumed execution preserves run linkage in events/timeline
  5. existing pause/resume behavior does not regress
  6. CircuitRunner.execute() produces paused_run_state on pause
  7. __paused_run_state__ in state is validated before resume proceeds
"""
from __future__ import annotations

import pytest
from src.engine.paused_run_state import PausedRunState, PausedRunStateError
from src.engine.node_execution_runtime import ReviewRequiredPause
from src.circuit.circuit_runner import (
    CircuitRunner,
    CircuitRunResult,
    ReviewGateResumeRequest,
)


# ── Shared fixtures ────────────────────────────────────────────────────────────

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
        self.events = []

    def execute_by_config_id(self, registry, config_id, state):
        class R:
            def __init__(self, o):
                self.output = o
        return R(self._outputs.get(config_id, f"out:{config_id}"))

    def _emit_event(self, event_type, payload, *, node_id=None):
        self.events.append((event_type, payload, node_id))

    def set_execution_id(self, eid):
        self._execution_id = eid


class _PausingRuntime(_SimpleRuntime):
    """Runtime that raises ReviewRequiredPause for a specific config_id."""

    def __init__(self, pause_config_id: str, outputs=None):
        super().__init__(outputs)
        self._pause_config_id = pause_config_id

    def execute_by_config_id(self, registry, config_id, state):
        if config_id == self._pause_config_id:
            raise ReviewRequiredPause(
                node_id="n_pause",
                payload={"reason": "human_review_required", "review_type": "quality"},
            )
        return super().execute_by_config_id(registry, config_id, state)


class _TrackingDeterminismRunner(CircuitRunner):
    def __init__(self, runtime, registry):
        super().__init__(runtime, registry)
        self.determinism_calls = []

    def _run_determinism_validation(self, circuit, *, strict_determinism=False):
        self.determinism_calls.append(strict_determinism)
        return super()._run_determinism_validation(
            circuit,
            strict_determinism=strict_determinism,
        )


def _reg(*config_ids):
    r = _SimpleRegistry()
    for cid in config_ids:
        r.register({"config_id": cid})
    return r


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PausedRunState model — unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPausedRunStateModel:

    def test_build_creates_frozen_immutable_state(self):
        prs = PausedRunState.build(
            paused_execution_id="exec-1",
            paused_node_id="n_b",
            completed_node_ids=frozenset({"n_a"}),
            review_required={"reason": "test"},
        )
        assert prs.paused_execution_id == "exec-1"
        assert prs.paused_node_id == "n_b"
        assert prs.completed_node_ids == frozenset({"n_a"})
        # Immutability: frozen dataclass must reject attribute assignment
        with pytest.raises((AttributeError, TypeError)):
            prs.paused_node_id = "hacked"  # type: ignore[misc]

    def test_completed_boundary_is_deterministic_safe(self):
        """The completed_node_ids boundary must be a frozenset — hashable and order-independent."""
        prs = PausedRunState.build(
            paused_execution_id="exec-2",
            paused_node_id="n_c",
            completed_node_ids=frozenset({"n_a", "n_b"}),
            review_required={},
        )
        assert isinstance(prs.completed_node_ids, frozenset)
        # Two builds with same inputs must produce equal boundaries
        prs2 = PausedRunState.build(
            paused_execution_id="exec-2",
            paused_node_id="n_c",
            completed_node_ids=frozenset({"n_b", "n_a"}),  # different order
            review_required={},
            now=prs.created_at,
        )
        assert prs.completed_node_ids == prs2.completed_node_ids

    def test_paused_node_not_in_completed(self):
        """Paused node must NOT be in completed_node_ids — it was not completed."""
        with pytest.raises(PausedRunStateError, match="paused_node_id.*must not appear in completed_node_ids"):
            PausedRunState.build(
                paused_execution_id="exec-bad",
                paused_node_id="n_b",
                completed_node_ids=frozenset({"n_a", "n_b"}),  # n_b is the paused node!
                review_required={},
            )

    def test_empty_paused_execution_id_rejected(self):
        with pytest.raises(PausedRunStateError, match="paused_execution_id"):
            PausedRunState.build(
                paused_execution_id="",
                paused_node_id="n_b",
                completed_node_ids=frozenset(),
                review_required={},
            )

    def test_empty_paused_node_id_rejected(self):
        with pytest.raises(PausedRunStateError, match="paused_node_id"):
            PausedRunState.build(
                paused_execution_id="exec-1",
                paused_node_id="",
                completed_node_ids=frozenset(),
                review_required={},
            )

    def test_serialise_round_trip(self):
        """to_dict / from_dict must produce an equivalent PausedRunState."""
        original = PausedRunState.build(
            paused_execution_id="exec-rt",
            paused_node_id="n_gate",
            completed_node_ids=frozenset({"n_a", "n_b"}),
            review_required={"reason": "quality_check"},
            previous_execution_id="exec-prior",
        )
        restored = PausedRunState.from_dict(original.to_dict())
        assert restored.paused_execution_id == original.paused_execution_id
        assert restored.paused_node_id == original.paused_node_id
        assert restored.completed_node_ids == original.completed_node_ids
        assert restored.required_revalidation == original.required_revalidation
        assert restored.previous_execution_id == original.previous_execution_id

    def test_from_dict_missing_required_field_raises(self):
        with pytest.raises(PausedRunStateError, match="missing field"):
            PausedRunState.from_dict({"paused_execution_id": "x"})  # missing most fields


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PausedRunState.validate_for_resume — stale/invalid rejection
# ═══════════════════════════════════════════════════════════════════════════════

class TestPausedRunStateValidation:

    def _nodes(self, *ids):
        return [{"id": nid} for nid in ids]

    def test_valid_state_passes(self):
        prs = PausedRunState.build(
            paused_execution_id="exec-1",
            paused_node_id="n_b",
            completed_node_ids=frozenset({"n_a"}),
            review_required={},
        )
        # Should not raise
        prs.validate_for_resume(self._nodes("n_a", "n_b", "n_c"))

    def test_stale_paused_node_id_rejected(self):
        """If paused_node_id is gone from the circuit, reject as stale."""
        prs = PausedRunState.build(
            paused_execution_id="exec-1",
            paused_node_id="n_b",
            completed_node_ids=frozenset(),
            review_required={},
        )
        with pytest.raises(PausedRunStateError, match="stale paused run state.*paused_node_id.*n_b"):
            prs.validate_for_resume(self._nodes("n_a", "n_c"))  # n_b removed

    def test_stale_completed_node_rejected(self):
        """If a completed node is gone from the circuit, reject as stale."""
        prs = PausedRunState.build(
            paused_execution_id="exec-1",
            paused_node_id="n_b",
            completed_node_ids=frozenset({"n_a"}),
            review_required={},
        )
        # n_a was completed but is now removed from circuit
        with pytest.raises(PausedRunStateError, match="stale paused run state.*completed nodes"):
            prs.validate_for_resume(self._nodes("n_b", "n_c"))  # n_a removed

    def test_empty_completed_set_is_valid(self):
        """Zero completed nodes is a valid boundary (nothing ran before pause)."""
        prs = PausedRunState.build(
            paused_execution_id="exec-1",
            paused_node_id="n_a",
            completed_node_ids=frozenset(),
            review_required={},
        )
        prs.validate_for_resume(self._nodes("n_a", "n_b"))


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CircuitRunner integration — paused_run_state is produced on pause
# ═══════════════════════════════════════════════════════════════════════════════

class TestCircuitRunnerPausedRunState:

    def _pausing_circuit(self):
        return {
            "id": "tc-pause",
            "nodes": [
                {"id": "n_a", "execution_config_ref": "cfg.a"},
                {"id": "n_pause", "execution_config_ref": "cfg.pause", "depends_on": ["n_a"]},
            ],
        }

    def _pausing_runner(self):
        rt = _PausingRuntime(pause_config_id="cfg.pause")
        reg = _reg("cfg.a", "cfg.pause")
        return CircuitRunner(rt, reg)

    def test_paused_result_has_paused_run_state(self):
        runner = self._pausing_runner()
        result = runner.execute(self._pausing_circuit(), {})
        assert result.governance.final_status == "paused"
        assert result.paused_run_state is not None

    def test_paused_run_state_paused_node_id_correct(self):
        runner = self._pausing_runner()
        result = runner.execute(self._pausing_circuit(), {})
        prs = result.paused_run_state
        assert prs.paused_node_id == "n_pause"

    def test_paused_run_state_completed_boundary_excludes_paused_node(self):
        """
        The completed_node_ids boundary must NOT include the paused node.
        n_a ran successfully; n_pause did not complete.
        """
        runner = self._pausing_runner()
        result = runner.execute(self._pausing_circuit(), {})
        prs = result.paused_run_state
        assert "n_pause" not in prs.completed_node_ids
        assert "n_a" in prs.completed_node_ids

    def test_paused_run_state_does_not_fake_completion(self):
        """
        The paused run state must NOT report n_pause as completed.
        Faking completion would break resume semantics.
        """
        runner = self._pausing_runner()
        result = runner.execute(self._pausing_circuit(), {})
        prs = result.paused_run_state
        # Paused node is not in completed set
        assert prs.paused_node_id not in prs.completed_node_ids
        # Governance knows execution was not completed
        assert result.governance.execution_completed is False

    def test_paused_run_state_is_none_on_success(self):
        rt = _SimpleRuntime()
        reg = _reg("cfg.a")
        runner = CircuitRunner(rt, reg)
        result = runner.execute(
            {"id": "tc", "nodes": [{"id": "n_a", "execution_config_ref": "cfg.a"}]},
            {},
        )
        assert result.paused_run_state is None
        assert result.governance.final_status == "success"

    def test_paused_run_state_carries_execution_id(self):
        runner = self._pausing_runner()
        result = runner.execute(self._pausing_circuit(), {})
        prs = result.paused_run_state
        assert prs.paused_execution_id  # non-empty
        # The execution_id in governance and in PausedRunState must match
        assert prs.paused_execution_id == result.governance.execution_id

    def test_paused_run_state_serialises_to_dict(self):
        runner = self._pausing_runner()
        result = runner.execute(self._pausing_circuit(), {})
        d = result.paused_run_state.to_dict()
        assert d["paused_node_id"] == "n_pause"
        assert "n_a" in d["completed_node_ids"]
        assert "n_pause" not in d["completed_node_ids"]
        assert isinstance(d["required_revalidation"], list)
        assert len(d["required_revalidation"]) > 0

    def test_paused_run_state_to_resume_request_payload(self):
        runner = self._pausing_runner()
        result = runner.execute(self._pausing_circuit(), {})
        payload = result.paused_run_state.to_resume_request_payload()
        assert payload["resume_from_node_id"] == "n_pause"
        assert payload["previous_execution_id"] == result.paused_run_state.paused_execution_id
        assert payload["requires_revalidation"] == [
            "structural_validation",
            "determinism_pre_validation",
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Resume with __paused_run_state__ — structural drift detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestResumeWithPausedRunState:

    def _two_node_circuit(self):
        return {
            "id": "tc",
            "nodes": [
                {"id": "n_a", "execution_config_ref": "cfg.a"},
                {"id": "n_b", "execution_config_ref": "cfg.b", "depends_on": ["n_a"]},
            ],
        }

    def _runner(self):
        rt = _SimpleRuntime({"cfg.a": "out-a", "cfg.b": "out-b"})
        reg = _reg("cfg.a", "cfg.b")
        return CircuitRunner(rt, reg)

    def _prs_dict(self, **kwargs):
        base = {
            "paused_execution_id": "exec-paused-1",
            "paused_node_id": "n_b",
            "previous_execution_id": None,
            "completed_node_ids": ["n_a"],
            "required_revalidation": ["structural_validation", "determinism_pre_validation"],
            "review_required": {"reason": "quality"},
            "created_at": "2024-01-01T00:00:00+00:00",
            "paused_at": "2024-01-01T00:00:00+00:00",
        }
        base.update(kwargs)
        return base

    def test_valid_paused_run_state_allows_resume(self):
        """A valid persisted pause state must allow resume to proceed."""
        runner = self._runner()
        state = {
            "__resume__": {
                "resume_from_node_id": "n_b",
                "previous_execution_id": "exec-paused-1",
            },
            "__paused_run_state__": self._prs_dict(),
            "__node_outputs__": {"n_a": "out-a"},
        }
        result = runner.execute(self._two_node_circuit(), state)
        assert result.governance.final_status == "success"

    def test_stale_paused_run_state_rejected_missing_paused_node(self):
        """If paused_node_id was removed from the circuit, resume must fail."""
        runner = self._runner()
        # paused_node_id = "n_missing" which doesn't exist in the circuit
        state = {
            "__resume__": {"resume_from_node_id": "n_b"},
            "__paused_run_state__": self._prs_dict(paused_node_id="n_missing"),
            "__node_outputs__": {"n_a": "out-a"},
        }
        with pytest.raises((ValueError, Exception), match="stale paused run state|n_missing"):
            runner.execute(self._two_node_circuit(), state)

    def test_stale_paused_run_state_rejected_missing_completed_node(self):
        """If a completed node no longer exists in the circuit, resume must fail."""
        runner = self._runner()
        state = {
            "__resume__": {"resume_from_node_id": "n_b"},
            "__paused_run_state__": self._prs_dict(completed_node_ids=["n_a", "n_removed"]),
            "__node_outputs__": {"n_a": "out-a"},
        }
        with pytest.raises((ValueError, Exception), match="stale paused run state|n_removed"):
            runner.execute(self._two_node_circuit(), state)

    def test_invalid_paused_run_state_dict_rejected(self):
        """A non-dict __paused_run_state__ must be rejected with TypeError."""
        runner = self._runner()
        state = {
            "__resume__": {"resume_from_node_id": "n_b"},
            "__paused_run_state__": "not-a-dict",
            "__node_outputs__": {"n_a": "out-a"},
        }
        with pytest.raises(TypeError, match="__paused_run_state__"):
            runner.execute(self._two_node_circuit(), state)

    def test_paused_run_state_consumed_from_state(self):
        """__paused_run_state__ must be consumed (popped) and not left in working state."""
        runner = self._runner()
        state = {
            "__resume__": {
                "resume_from_node_id": "n_b",
                "previous_execution_id": "exec-paused-1",
            },
            "__paused_run_state__": self._prs_dict(),
            "__node_outputs__": {"n_a": "out-a"},
        }
        result = runner.execute(self._two_node_circuit(), state)
        assert "__paused_run_state__" not in result

    def test_resume_node_mismatch_with_persisted_state_rejected(self):
        """
        If __paused_run_state__ records paused_node_id='n_b' but
        __resume__.resume_from_node_id='n_a', the call must be rejected.
        The durable boundary must be respected exactly.
        """
        runner = self._runner()
        state = {
            "__resume__": {
                "resume_from_node_id": "n_a",   # mismatch: prs says n_b
            },
            "__paused_run_state__": self._prs_dict(),  # paused_node_id = "n_b"
            "__node_outputs__": {"n_a": "out-a"},
        }
        with pytest.raises(ValueError, match="resume_from_node_id.*n_a.*paused_node_id.*n_b|paused_node_id.*n_b.*resume_from_node_id.*n_a"):
            runner.execute(self._two_node_circuit(), state)

    def test_paused_run_state_without_resume_is_rejected(self):
        """
        __paused_run_state__ present but __resume__ absent must be rejected.
        Auto-deriving resume target is explicitly not supported (Option A).
        """
        runner = self._runner()
        state = {
            # no __resume__ key
            "__paused_run_state__": self._prs_dict(),
            "__node_outputs__": {"n_a": "out-a"},
        }
        with pytest.raises(ValueError, match="__paused_run_state__.*__resume__ is absent"):
            runner.execute(self._two_node_circuit(), state)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Resume run linkage preservation in events/timeline
# ═══════════════════════════════════════════════════════════════════════════════

class TestResumeRunLinkage:

    def _pausing_circuit(self):
        return {
            "id": "tc-linkage",
            "nodes": [
                {"id": "n_a", "execution_config_ref": "cfg.a"},
                {"id": "n_pause", "execution_config_ref": "cfg.pause", "depends_on": ["n_a"]},
                {"id": "n_b", "execution_config_ref": "cfg.b", "depends_on": ["n_pause"]},
            ],
        }

    def test_resumed_execution_emits_execution_resumed_event(self):
        """A resume run must emit execution_resumed with prior linkage."""
        rt = _SimpleRuntime({"cfg.a": "out-a", "cfg.b": "out-b"})
        reg = _reg("cfg.a", "cfg.pause", "cfg.b")
        runner = CircuitRunner(rt, reg)
        state = {
            "__resume__": {
                "resume_from_node_id": "n_pause",
                "previous_execution_id": "exec-first-run",
            },
            "__node_outputs__": {"n_a": "out-a"},
        }
        circuit = {
            "id": "tc-resume",
            "nodes": [
                {"id": "n_a", "execution_config_ref": "cfg.a"},
                {"id": "n_pause", "execution_config_ref": "cfg.pause", "depends_on": ["n_a"]},
            ],
        }
        runner.execute(circuit, state)

        event_types = [e[0] for e in rt.events]
        assert "execution_resumed" in event_types

        resumed_event = next(e for e in rt.events if e[0] == "execution_resumed")
        assert resumed_event[1].get("previous_execution_id") == "exec-first-run"

    def test_resumed_run_is_resume_flagged_in_started_event(self):
        """execution_started for a resume run must have is_resume == True."""
        rt = _SimpleRuntime({"cfg.a": "out-a", "cfg.b": "out-b"})
        reg = _reg("cfg.a", "cfg.b")
        runner = CircuitRunner(rt, reg)
        circuit = {
            "id": "tc",
            "nodes": [
                {"id": "n_a", "execution_config_ref": "cfg.a"},
                {"id": "n_b", "execution_config_ref": "cfg.b", "depends_on": ["n_a"]},
            ],
        }
        state = {
            "__resume__": {"resume_from_node_id": "n_b"},
            "__node_outputs__": {"n_a": "out-a"},
        }
        runner.execute(circuit, state)
        started = next(e for e in rt.events if e[0] == "execution_started")
        assert started[1]["is_resume"] is True

    def test_paused_run_state_previous_execution_id_from_prior_resume(self):
        """
        If a paused run was itself a resume of a prior run, its PausedRunState
        must carry the prior run's previous_execution_id.
        """
        rt = _PausingRuntime(pause_config_id="cfg.pause")
        reg = _reg("cfg.a", "cfg.pause")
        runner = CircuitRunner(rt, reg)
        circuit = {
            "id": "tc",
            "nodes": [
                {"id": "n_a", "execution_config_ref": "cfg.a"},
                {"id": "n_pause", "execution_config_ref": "cfg.pause", "depends_on": ["n_a"]},
            ],
        }
        # Simulate: this is itself a resume run
        state = {
            "__resume__": {
                "resume_from_node_id": "n_a",
                "previous_execution_id": "exec-original",
            },
            "__node_outputs__": {},
        }
        result = runner.execute(circuit, state)
        assert result.governance.final_status == "paused"
        prs = result.paused_run_state
        # The chain: exec-original → this run → paused
        assert prs.previous_execution_id == "exec-original"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Regression: existing pause/resume behavior must not regress
# ═══════════════════════════════════════════════════════════════════════════════

class TestPauseResumeRegression:

    def test_pause_without_paused_run_state_still_works(self):
        """Classic pause via ReviewRequiredPause without PausedRunState must still work."""
        rt = _PausingRuntime(pause_config_id="cfg.pause")
        reg = _reg("cfg.a", "cfg.pause")
        runner = CircuitRunner(rt, reg)
        circuit = {
            "id": "tc",
            "nodes": [
                {"id": "n_a", "execution_config_ref": "cfg.a"},
                {"id": "n_pause", "execution_config_ref": "cfg.pause", "depends_on": ["n_a"]},
            ],
        }
        result = runner.execute(circuit, {})
        assert result.governance.final_status == "paused"

        paused_event = next(e for e in rt.events if e[0] == "execution_paused")
        assert paused_event[1]["resume"]["can_resume"] is True
        assert paused_event[1]["resume"]["resume_from_node_id"] == "n_pause"

    def test_resume_without_paused_run_state_still_works(self):
        """Classic __resume__ without __paused_run_state__ must still proceed."""
        rt = _SimpleRuntime({"cfg.a": "out-a", "cfg.b": "out-b"})
        reg = _reg("cfg.a", "cfg.b")
        runner = CircuitRunner(rt, reg)
        circuit = {
            "id": "tc",
            "nodes": [
                {"id": "n_a", "execution_config_ref": "cfg.a"},
                {"id": "n_b", "execution_config_ref": "cfg.b", "depends_on": ["n_a"]},
            ],
        }
        state = {
            "__resume__": {"resume_from_node_id": "n_b"},
            "__node_outputs__": {"n_a": "out-a"},
        }
        result = runner.execute(circuit, state)
        assert result.governance.final_status == "success"
        assert result["n_b"] == "out-b"

    def test_paused_semantics_distinct_from_failed(self):
        """Paused must not be misclassified as failed."""
        rt = _PausingRuntime(pause_config_id="cfg.pause")
        reg = _reg("cfg.a", "cfg.pause")
        runner = CircuitRunner(rt, reg)
        circuit = {
            "id": "tc",
            "nodes": [
                {"id": "n_a", "execution_config_ref": "cfg.a"},
                {"id": "n_pause", "execution_config_ref": "cfg.pause", "depends_on": ["n_a"]},
            ],
        }
        result = runner.execute(circuit, {})
        gov = result.governance
        assert gov.final_status == "paused"
        assert gov.final_status != "failed"
        assert gov.execution_completed is False

    def test_no_paused_run_state_on_failure(self):
        """On a real failure (exception), paused_run_state must remain None."""
        class _FailRuntime(_SimpleRuntime):
            def execute_by_config_id(self, registry, config_id, state):
                raise RuntimeError("hard failure")

        rt = _FailRuntime()
        reg = _reg("cfg.a")
        runner = CircuitRunner(rt, reg)
        circuit = {"id": "tc", "nodes": [{"id": "n_a", "execution_config_ref": "cfg.a"}]}
        with pytest.raises(RuntimeError):
            runner.execute(circuit, {})
