# SAFE_MODE metrics enhanced runner
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Callable

import json
import os
import traceback
import time
from pathlib import Path

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

    def __init__(
        self,
        meta: RunMeta,
        run_dir: str,
        *,
        max_total_steps: int = 50,
        max_attempts_per_gate: int = 3,
        auto_retry_policy_refusal: bool = True,
        auto_retry_too_long: bool = True,
        auto_retry_transient: bool = True,
        retry_backoff_seconds: float = 1.0,
    ):
        self.meta = meta
        self.run_dir = run_dir
        self.executors: Dict[GateId, GateExecutor] = {}
        self.max_total_steps = max_total_steps
        self.max_attempts_per_gate = max_attempts_per_gate
        self._steps_executed = 0

        self.auto_retry_policy_refusal = auto_retry_policy_refusal
        self.auto_retry_too_long = auto_retry_too_long
        self.auto_retry_transient = auto_retry_transient
        self.retry_backoff_seconds = retry_backoff_seconds

        if not hasattr(self.meta, "safe_mode_metrics"):
            self.meta.safe_mode_metrics = {
                "total": 0,
                "by_gate": {},
                "by_category": {}
            }

    def register(self, gate_id: GateId, executor: GateExecutor) -> None:
        self.executors[gate_id] = executor

    def _record_safe_mode_metrics(self, gate: GateId, category: str):
        metrics = self.meta.safe_mode_metrics
        metrics["total"] += 1
        metrics["by_gate"][gate.value] = metrics["by_gate"].get(gate.value, 0) + 1
        metrics["by_category"][category] = metrics["by_category"].get(category, 0) + 1

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
        self.meta.attempts["STOP_REASON"] = reason

    def _classify_error(self, err: BaseException) -> str:
        msg = f"{type(err).__name__}: {err}".lower()
        if any(p in msg for p in ["policy", "refus", "safety", "violates"]):
            return "POLICY_REFUSAL"
        if any(p in msg for p in ["too long", "context", "token limit"]):
            return "TOO_LONG"
        if any(p in msg for p in ["timeout", "rate limit", "503", "network"]):
            return "TRANSIENT_ERROR"
        if any(p in msg for p in ["invalid", "schema", "json"]):
            return "INVALID_REQUEST"
        return "UNKNOWN_ERROR"

    def _should_autoretry(self, category: str) -> bool:
        if category == "POLICY_REFUSAL":
            return self.auto_retry_policy_refusal
        if category == "TOO_LONG":
            return self.auto_retry_too_long
        if category == "TRANSIENT_ERROR":
            return self.auto_retry_transient
        return False

    def _next_gate(self, gate: GateId, decision: Decision) -> GateId:
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
            return GateId.G7
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
        if self._steps_executed >= self.max_total_steps:
            self._stop_run("max_total_steps exceeded")
            return False

        gate = self.meta.current_gate
        if gate in (GateId.DONE, GateId.STOP):
            return False

        executor = self.executors.get(gate)
        if executor is None:
            raise RuntimeError(f"No executor registered for gate {gate}")

        self.meta.attempts[gate.value] = self.meta.attempts.get(gate.value, 0) + 1
        ctx = GateContext(meta=self.meta, run_dir=self.run_dir)

        retries_left = 1

        while True:
            try:
                result = executor(ctx)
                spec = standard_spec(gate.value)
                spec.validate(result.outputs)
                break
            except Exception as err:
                category = self._classify_error(err)
                if retries_left > 0 and self._should_autoretry(category):
                    retries_left -= 1
                    self._record_safe_mode_metrics(gate, category)
                    if category == "TRANSIENT_ERROR":
                        time.sleep(self.retry_backoff_seconds)
                    continue
                self._stop_run(f"{category}: {err}")
                return False

        next_gate = self._next_gate(gate, result.decision)
        self._record_transition(gate, next_gate, result.decision)
        self._steps_executed += 1
        return next_gate not in (GateId.DONE, GateId.STOP)

    def run(self) -> RunMeta:
        self.meta.status = RunStatus.RUNNING
        while self.step():
            pass
        return self.meta
