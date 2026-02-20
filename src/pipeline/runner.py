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

    - Enforces artifact contracts per gate.
    - Converts gate crashes/contract violations into STOP (never crash the runner).
    - Includes safety stops to prevent infinite loops.
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
        self.meta.status = RunStatus.STOP
        self.meta.current_gate = GateId.STOP
        self.meta.stop_reason = reason

    def _next_gate(self, gate: GateId, decision: Decision) -> GateId:
        # Gate-requested STOP
        if decision == Decision.STOP:
            if not self.meta.stop_reason:
                self.meta.stop_reason = "STOP requested by gate"
            self.meta.status = RunStatus.STOP
            return GateId.STOP

        if gate == GateId.G1:
            return GateId.G2 if decision == Decision.PASS else GateId.G1
        if gate == GateId.G2:
            return GateId.G3 if decision == Decision.PASS else GateId.G1
        if gate == GateId.G3:
            return GateId.G4 if decision == Decision.PASS else GateId.G1
        if gate == GateId.G4:
            return GateId.G5 if decision == Decision.PASS else GateId.G1
        if gate == GateId.G5:
            return GateId.G6 if decision == Decision.PASS else GateId.G4
        if gate == GateId.G6:
            # Policy invariant: G6 FAIL must return control to G4 (handover).
            if decision == Decision.FAIL:
                return GateId.G4
            return GateId.G7
        if gate == GateId.G7:
            if decision == Decision.PASS:
                self.meta.status = RunStatus.PASS
                return GateId.DONE
            if decision == Decision.FAIL:
                self.meta.status = RunStatus.FAIL
                return GateId.G5
            self.meta.status = RunStatus.STOP
            if not self.meta.stop_reason:
                self.meta.stop_reason = "STOP requested by gate"
            return GateId.STOP
        return GateId.STOP

    def step(self) -> bool:
        """Execute one gate. Returns False if pipeline should stop."""
        # total-step safety
        if self._steps_executed >= self.max_total_steps:
            self._stop_run(f"max_total_steps exceeded: {self.max_total_steps}")
            return False

        gate = self.meta.current_gate
        if gate in (GateId.DONE, GateId.STOP):
            return False

        executor = self.executors.get(gate)
        if executor is None:
            # This is a developer error; STOP instead of raising to keep invariants.
            self._stop_run(f"NO_EXECUTOR: {gate.value}")
            return False

        # attempt count
        self.meta.attempts[gate.value] = self.meta.attempts.get(gate.value, 0) + 1

        # per-gate safety
        if self.meta.attempts[gate.value] > self.max_attempts_per_gate:
            self._stop_run(f"max_attempts_per_gate exceeded: {gate.value} > {self.max_attempts_per_gate}")
            # record terminal transition
            self._record_transition(gate, GateId.STOP, Decision.STOP)
            return False

        ctx = GateContext(meta=self.meta, run_dir=self.run_dir)

        # Execute gate safely: any crash becomes STOP.
        try:
            result = executor(ctx)
        except Exception as e:  # noqa: BLE001
            self._stop_run(f"GATE_EXCEPTION: {gate.value}: {type(e).__name__}: {e}")
            self._record_transition(gate, GateId.STOP, Decision.STOP)
            self._steps_executed += 1
            return False

        # Enforce artifact contract safely: contract violations become STOP.
        try:
            spec = standard_spec(gate.value)
            spec.validate(result.outputs)
        except Exception as e:  # noqa: BLE001
            self._stop_run(f"CONTRACT_VIOLATION: {gate.value}: {type(e).__name__}: {e}")
            self._record_transition(gate, GateId.STOP, Decision.STOP)
            self._steps_executed += 1
            return False

        next_gate = self._next_gate(gate, result.decision)
        self._record_transition(gate, next_gate, result.decision)

        self._steps_executed += 1
        return next_gate not in (GateId.DONE, GateId.STOP)

    def run(self) -> RunMeta:
        """Run until DONE or STOP."""
        self.meta.status = RunStatus.RUNNING
        if getattr(self.meta, "current_gate", None) in (None, GateId.DONE, GateId.STOP):
            self.meta.current_gate = GateId.G1
        while self.step():
            pass
        return self.meta
