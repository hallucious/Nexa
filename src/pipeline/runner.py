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
    """
    Executes a 7-Gate state machine and enforces artifact contracts per gate.

    Global (all-gates) refusal/error handling policy:
    - Every gate call is wrapped by the runner.
    - Errors are classified into a small stable set.
    - Runner writes deterministic error artifacts and STOPs (no crashes).
    - Optional auto-retry: for certain categories, the SAME gate is re-called once
      with a global SAFE_MODE signal (env var), without any gate-specific logic.
    """

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

        # Auto-retry toggles (global, all gates)
        self.auto_retry_policy_refusal = auto_retry_policy_refusal
        self.auto_retry_too_long = auto_retry_too_long
        self.auto_retry_transient = auto_retry_transient
        self.retry_backoff_seconds = retry_backoff_seconds

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
        self.meta.attempts["STOP_REASON"] = reason  # lightweight trace

    def _classify_error(self, err: BaseException) -> str:
        """Classify any error into a small stable set."""
        msg = f"{type(err).__name__}: {err}"
        m = msg.lower()

        # Policy/refusal-like signals (best-effort, provider-agnostic)
        policy_markers = [
            "policy", "refus", "safety", "content policy", "request was rejected",
            "violates", "moderation", "blocked", "not allowed",
        ]
        if any(p in m for p in policy_markers):
            return "POLICY_REFUSAL"

        # Too-long / context / token limit signals
        too_long_markers = [
            "too long", "context length", "maximum context", "token limit",
            "max tokens", "request too large", "payload too large", "413",
        ]
        if any(p in m for p in too_long_markers):
            return "TOO_LONG"

        # Invalid request / schema / validation
        invalid_markers = [
            "invalid", "schema", "json", "validation", "contract",
            "missing", "field required", "bad request", "400",
        ]
        if any(p in m for p in invalid_markers):
            return "INVALID_REQUEST"

        # Transient-ish (network/timeouts/5xx/rate limits)
        transient_markers = [
            "timeout", "timed out", "temporarily", "try again", "rate limit",
            "429", "502", "503", "504", "connection", "network",
        ]
        if any(p in m for p in transient_markers):
            return "TRANSIENT_ERROR"

        return "UNKNOWN_ERROR"

    def _write_gate_error_artifacts(self, gate: GateId, category: str, err: BaseException) -> None:
        """Write deterministic error artifacts without requiring any gate-specific logic."""
        run_dir = Path(self.run_dir)
        stamp = now_seoul().isoformat()

        meta = {
            "at": stamp,
            "gate": gate.value,
            "category": category,
            "error_type": type(err).__name__,
            "error_message": str(err),
        }
        (run_dir / f"{gate.value}_ERROR_META.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        tb = traceback.format_exc()
        (run_dir / f"{gate.value}_ERROR.md").write_text(
            "# GATE ERROR\n\n"
            f"- gate: {gate.value}\n"
            f"- category: {category}\n"
            f"- at: {stamp}\n\n"
            "## Exception\n"
            f"```\n{type(err).__name__}: {err}\n```\n\n"
            "## Traceback\n"
            f"```\n{tb}\n```\n",
            encoding="utf-8",
        )

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

    def _should_autoretry(self, category: str) -> bool:
        if category == "POLICY_REFUSAL":
            return self.auto_retry_policy_refusal
        if category == "TOO_LONG":
            return self.auto_retry_too_long
        if category == "TRANSIENT_ERROR":
            return self.auto_retry_transient
        return False

    def step(self) -> bool:
        """Execute one gate. Returns False if pipeline should stop."""
        if self._steps_executed >= self.max_total_steps:
            self._stop_run(f"max_total_steps exceeded: {self.max_total_steps}")
            return False

        gate = self.meta.current_gate
        if gate in (GateId.DONE, GateId.STOP):
            return False

        executor = self.executors.get(gate)
        if executor is None:
            raise RuntimeError(f"No executor registered for gate {gate}")

        # attempt count (per gate)
        self.meta.attempts[gate.value] = self.meta.attempts.get(gate.value, 0) + 1
        if self.meta.attempts[gate.value] > self.max_attempts_per_gate:
            self._stop_run(f"max_attempts_per_gate exceeded: {gate.value} > {self.max_attempts_per_gate}")
            return False

        ctx = GateContext(meta=self.meta, run_dir=self.run_dir)

        # local auto-retry budget for THIS step call (uniform across gates)
        retries_left = 1  # at most 1 auto-retry on classified categories

        while True:
            try:
                result = executor(ctx)

                # enforce artifact contract
                spec = standard_spec(gate.value)
                spec.validate(result.outputs)

                break  # success

            except Exception as err:
                category = self._classify_error(err)

                # Auto-retry path: re-call same gate once with a global SAFE_MODE signal
                if retries_left > 0 and self._should_autoretry(category):
                    retries_left -= 1

                    # Global hint for providers/gates.
                    # If ignored, retry is harmless; if honored, enables safe-mode re-ask.
                    os.environ["HAI_SAFE_MODE"] = "1"
                    os.environ["HAI_SAFE_MODE_REASON"] = category
                    os.environ["HAI_SAFE_MODE_GATE"] = gate.value

                    # small backoff for transient errors
                    if category == "TRANSIENT_ERROR" and self.retry_backoff_seconds > 0:
                        time.sleep(self.retry_backoff_seconds)

                    continue  # retry same gate

                # No retry (or retry exhausted): write artifacts & STOP deterministically
                self._write_gate_error_artifacts(gate, category, err)
                self._stop_run(f"{category}: {type(err).__name__}: {err}")
                return False

        next_gate = self._next_gate(gate, result.decision)
        self._record_transition(gate, next_gate, result.decision)

        self._steps_executed += 1
        return next_gate not in (GateId.DONE, GateId.STOP)

    def run(self) -> RunMeta:
        """Run until DONE or STOP (including safety stop)."""
        self.meta.status = RunStatus.RUNNING
        while self.step():
            pass
        return self.meta
