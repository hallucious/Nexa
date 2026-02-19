from dataclasses import dataclass
from typing import Dict, Callable

from src.pipeline.state import RunMeta, GateId, RunStatus
from src.models.decision_models import Decision, Transition, GateResult
from src.pipeline.contracts import standard_spec
from src.utils.time import now_seoul


@dataclass
class GateContext:
    meta: RunMeta
    run_dir: str


GateExecutor = Callable[[GateContext], GateResult]


class PipelineRunner:
    """
    Executes a 7-Gate state machine.
    Enforces artifact contracts per gate.
    Includes safety stops to prevent infinite loops.
    """

    def __init__(
        self,
        meta: RunMeta,
        run_dir: str,
        *,
        max_total_steps: int = 50,
        max_attempts_per_gate: int = 3,
    ):
        self.meta = meta
        self.run_dir = run_dir
        self.executors: Dict[GateId, GateExecutor] = {}
        self.max_total_steps = max_total_steps
        self.max_attempts_per_gate = max_attempts_per_gate
        self._steps_executed = 0

    def register(self, gate_id: GateId, executor: GateExecutor) -> None:
        self.executors[gate_id] = executor

    def _record_transition(self, from_gate: GateId, to_gate: GateId, decision: Decision) -> None:
        self.meta.transitions.append(
            Transition(
                from_gate=from_gate.value,
                to_gate=to_gate.value,
                decision=decision,
                at=now_seoul().isoformat(),
            )
        )
        self.meta.current_gate = to_gate

    def _stop_run(self, reason: str) -> None:
        # Mark STOP and move to STOP gate
        self.meta.status = RunStatus.STOP
        # keep current gate for traceability, but set to STOP as terminal
        self.meta.current_gate = GateId.STOP
        # Optionally, you could write reason somewhere later; for now keep in attempts
        self.meta.attempts["STOP_REASON"] = reason  # lightweight trace

    def _next_gate(self, gate: GateId, decision: Decision) -> GateId:
        # Hard terminal: STOP always ends the run.
        if decision.is_stop:
            self.meta.status = RunStatus.STOP
            return GateId.STOP

        # Deterministic transition table (keeps behavior identical, improves clarity).
        linear_transitions: Dict[GateId, Dict[Decision, GateId]] = {
            GateId.G1: {Decision.PASS: GateId.G2, Decision.FAIL: GateId.G1},
            GateId.G2: {Decision.PASS: GateId.G3, Decision.FAIL: GateId.G1},
            GateId.G3: {Decision.PASS: GateId.G4, Decision.FAIL: GateId.G1},
            GateId.G4: {Decision.PASS: GateId.G5, Decision.FAIL: GateId.G1},
            GateId.G5: {Decision.PASS: GateId.G6, Decision.FAIL: GateId.G4},
            # Gate6 is advisory by design; it should never FAIL, but we keep a safe fallback.
            GateId.G6: {Decision.PASS: GateId.G7, Decision.FAIL: GateId.G4},
        }

        if gate in linear_transitions:
            return linear_transitions[gate].get(decision, GateId.STOP)

        if gate == GateId.G7:
            if decision.is_pass:
                self.meta.status = RunStatus.PASS
                return GateId.DONE
            if decision.is_fail:
                self.meta.status = RunStatus.FAIL
                return GateId.G5
            # Defensive fallback (should be unreachable with the current Decision enum).
            self.meta.status = RunStatus.STOP
            return GateId.STOP

        return GateId.STOP

    def step(self) -> bool:
        """
        Execute one gate.
        Returns False if pipeline should stop.
        """
        # total-step safety
        if self._steps_executed >= self.max_total_steps:
            self._stop_run(f"max_total_steps exceeded: {self.max_total_steps}")
            return False

        gate = self.meta.current_gate
        if gate in (GateId.DONE, GateId.STOP):
            return False

        executor = self.executors.get(gate)
        if executor is None:
            raise RuntimeError(f"No executor registered for gate {gate}")

        # attempt count
        self.meta.attempts[gate.value] = self.meta.attempts.get(gate.value, 0) + 1

        # per-gate safety (prevents infinite loops like G2 FAIL -> G1 -> G2 FAIL ...)
        if self.meta.attempts[gate.value] > self.max_attempts_per_gate:
            self._stop_run(f"max_attempts_per_gate exceeded: {gate.value} > {self.max_attempts_per_gate}")
            return False

        ctx = GateContext(meta=self.meta, run_dir=self.run_dir)
        result = executor(ctx)

        # enforce artifact contract
        spec = standard_spec(gate.value)
        spec.validate(result.outputs)

        next_gate = self._next_gate(gate, result.decision)
        self._record_transition(gate, next_gate, result.decision)

        self._steps_executed += 1
        return next_gate not in (GateId.DONE, GateId.STOP)

    def run(self) -> RunMeta:
        """
        Run until DONE or STOP (including safety stop).
        """
        self.meta.status = RunStatus.RUNNING
        # Defensive: a fresh run should start at G1.
        if getattr(self.meta, 'current_gate', None) in (None, GateId.DONE, GateId.STOP):
            self.meta.current_gate = GateId.G1
        while self.step():
            pass
        return self.meta