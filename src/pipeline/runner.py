from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Callable

from src.pipeline.state import RunMeta, GateId, RunStatus
from src.models.decision_models import Decision, Transition, GateResult
from src.utils.time import now_seoul


@dataclass
class GateContext:
    meta: RunMeta
    run_dir: str


GateExecutor = Callable[[GateContext], GateResult]


class PipelineRunner:
    """
    Executes a 7-Gate state machine.
    Gate logic itself is injected (mock or real).
    """

    def __init__(self, meta: RunMeta, run_dir: str):
        self.meta = meta
        self.run_dir = run_dir
        self.executors: Dict[GateId, GateExecutor] = {}

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

    def _next_gate(self, gate: GateId, decision: Decision) -> GateId:
        """
        Transition table (Step 2 fixed)
        """
        if gate == GateId.G1:
            return GateId.G2 if decision == Decision.PASS else GateId.STOP

        if gate == GateId.G2:
            return GateId.G3 if decision == Decision.PASS else GateId.G1

        if gate == GateId.G3:
            return GateId.G4 if decision == Decision.PASS else GateId.G1

        if gate == GateId.G4:
            return GateId.G5 if decision == Decision.PASS else GateId.G1

        if gate == GateId.G5:
            return GateId.G6 if decision == Decision.PASS else GateId.G4

        if gate == GateId.G6:
            return GateId.G7  # info-only gate

        if gate == GateId.G7:
            if decision == Decision.PASS:
                self.meta.status = RunStatus.PASS
                return GateId.DONE
            if decision == Decision.FAIL:
                self.meta.status = RunStatus.FAIL
                return GateId.G5
            self.meta.status = RunStatus.STOP
            return GateId.STOP

        return GateId.STOP

    def step(self) -> bool:
        """
        Execute one gate.
        Returns False if pipeline should stop.
        """
        gate = self.meta.current_gate
        if gate in (GateId.DONE, GateId.STOP):
            return False

        executor = self.executors.get(gate)
        if executor is None:
            raise RuntimeError(f"No executor registered for gate {gate}")

        # attempt count
        self.meta.attempts[gate.value] = self.meta.attempts.get(gate.value, 0) + 1

        ctx = GateContext(meta=self.meta, run_dir=self.run_dir)
        result = executor(ctx)

        next_gate = self._next_gate(gate, result.decision)
        self._record_transition(gate, next_gate, result.decision)

        return next_gate not in (GateId.DONE, GateId.STOP)

    def run(self) -> RunMeta:
        """
        Run until DONE or STOP.
        """
        self.meta.status = RunStatus.RUNNING
        while self.step():
            pass
        return self.meta
