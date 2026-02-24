from dataclasses import dataclass, asdict
import json
import time
from typing import Dict, Callable, Any, Optional
from pathlib import Path

from src.pipeline.state import RunMeta, GateId, RunStatus
from src.models.decision_models import Decision, Transition, GateResult
from src.pipeline.stop_reason import StopReason, is_valid_stop_reason
from src.utils.time import now_seoul
from src.pipeline.registry import GateRegistry
from src.contracts.validator import ContractValidator


@dataclass
class GateContext:
    meta: RunMeta
    run_dir: str
    # Optional shared context for dependency injection (tools/providers/config).
    # v0 contract: gates MUST NOT rely on this being non-empty.
    context: Dict[str, Any]
    # Optional provider bundle for external AI calls (gpt/gemini/claude/perplexity/codex).
    # v0 contract: gates MUST NOT rely on specific keys being present.
    providers: Dict[str, Any]


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
        context: Optional[Dict[str, Any]] = None,
        providers: Optional[Dict[str, Any]] = None,
        max_total_steps: int = 50,
        max_attempts_per_gate: int = 3,
    ):
        self.meta = meta
        self.run_dir = run_dir
        self.registry = GateRegistry()
        self.context: Dict[str, Any] = dict(context or {})
        self.providers: Dict[str, Any] = dict(providers or {})
        self.max_total_steps = max_total_steps
        self.max_attempts_per_gate = max_attempts_per_gate
        self._steps_executed = 0

    def register(self, gate_id: GateId, executor: GateExecutor) -> None:
        self.registry.register(gate_id, executor)

    def registered_gates(self) -> Dict[str, str]:
        """Return a human-friendly snapshot of registered gates.

        v0 introspection only; not used for execution logic.
        """

        out: Dict[str, str] = {}
        for gid, ex in self.registry.items():
            out[gid.value] = getattr(ex, "__name__", ex.__class__.__name__)
        return out

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

    def _write_meta_json(self) -> None:
        """Persist run-level META.json for observability and reproducibility.

        Must be written for any terminal status (PASS/FAIL/STOP). Best-effort: never raises.
        """
        try:
            Path(self.run_dir).mkdir(parents=True, exist_ok=True)
            meta_path = Path(self.run_dir) / "META.json"
            payload = asdict(self.meta)
            # Ensure enums are serialized as their value if present.
            payload["status"] = getattr(self.meta.status, "value", self.meta.status)
            payload["current_gate"] = getattr(self.meta.current_gate, "value", self.meta.current_gate)
            with meta_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            # Never let metadata persistence crash the runner.
            return


    def _stop_run(self, detail: str) -> None:
        """Stop the run with a standardized reason code.

        Internal/runner-triggered stops are categorized as INTERNAL_ERROR.
        The human-readable detail is recorded into gate_metrics for audit.
        """

        self.meta.status = RunStatus.STOP
        self.meta.current_gate = GateId.STOP
        self.meta.stop_reason = StopReason.INTERNAL_ERROR.value
        try:
            self.meta.gate_metrics.setdefault("_runner", {})["stop_detail"] = str(detail)
        except Exception:
            pass


    def _inject_observability(
        self,
        *,
        gate_id: GateId,
        result: GateResult,
        started_at: str,
        finished_at: str,
        execution_time_ms: int,
    ) -> None:
        """Attach basic observability fields into GateResult.meta.

        Contract:
        - These fields are additive and must not affect PASS/FAIL/STOP semantics.
        - provider_latency_ms is optional and may be set by gates/providers.
        """
        if result.meta is None:
            result.meta = {}
        if isinstance(result.meta, dict):
            result.meta.setdefault("started_at", started_at)
            result.meta.setdefault("finished_at", finished_at)
            result.meta.setdefault("execution_time_ms", execution_time_ms)

    def _next_gate(self, gate: GateId, decision: Decision) -> GateId:
        # Gate-requested STOP
        if decision == Decision.STOP:
            if not self.meta.stop_reason:
                self.meta.stop_reason = StopReason.STOP_REQUESTED.value
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
                self.meta.stop_reason = StopReason.STOP_REQUESTED.value
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

        executor = self.registry.get(gate)
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

        ctx = GateContext(meta=self.meta, run_dir=self.run_dir, context=self.context, providers=self.providers)

        # Observability (C): measure execution time and attach timestamps.
        started_at = now_seoul().isoformat()
        t0 = time.perf_counter()

        # Execute gate safely: any crash becomes STOP.
        try:
            result = executor(ctx)
        except Exception as e:  # noqa: BLE001
            self._stop_run(f"GATE_EXCEPTION: {gate.value}: {type(e).__name__}: {e}")
            self._record_transition(gate, GateId.STOP, Decision.STOP)
            self._steps_executed += 1
            return False

        finished_at = now_seoul().isoformat()
        execution_time_ms = int((time.perf_counter() - t0) * 1000)

        # Attach observability into result.meta (additive; never changes semantics).
        if getattr(result, "meta", None) is None:
            result.meta = {}
        if isinstance(result.meta, dict):
            result.meta.setdefault("started_at", started_at)
            result.meta.setdefault("finished_at", finished_at)
            result.meta.setdefault("execution_time_ms", execution_time_ms)

        # Persist observability into run-level gate_metrics (for audit / debugging).
        try:
            gm = self.meta.gate_metrics.setdefault(gate.value, {})
            if isinstance(gm, dict):
                gm.setdefault("started_at", started_at)
                gm.setdefault("finished_at", finished_at)
                gm.setdefault("execution_time_ms", execution_time_ms)
                # provider_latency_ms is optional; if gate provided it, keep it.
                if isinstance(result.meta, dict) and "provider_latency_ms" in result.meta:
                    gm.setdefault("provider_latency_ms", result.meta.get("provider_latency_ms"))
        except Exception:
            pass

        # Best-effort: patch per-gate META.json artifact if it exists in outputs.
        try:
            meta_key = f"{gate.value}_META.json"
            meta_file = None
            if isinstance(result.outputs, dict):
                meta_file = result.outputs.get(meta_key)
            if isinstance(meta_file, str) and meta_file.strip():
                meta_path = Path(self.run_dir) / meta_file
                if meta_path.exists():
                    payload = json.loads(meta_path.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        payload.setdefault("started_at", started_at)
                        payload.setdefault("finished_at", finished_at)
                        payload.setdefault("execution_time_ms", execution_time_ms)
                        if isinstance(result.meta, dict) and "provider_latency_ms" in result.meta:
                            payload.setdefault("provider_latency_ms", result.meta.get("provider_latency_ms"))
                        meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

            return False

        # Enforce artifact contract safely at Runner level.
        try:
            ContractValidator.validate_gate_outputs(gate.value, result.outputs)
        except Exception as e:  # noqa: BLE001
            self._stop_run(f"CONTRACT_VIOLATION: {gate.value}: {type(e).__name__}: {e}")
            self._record_transition(gate, GateId.STOP, Decision.STOP)
            self._steps_executed += 1
            return False


        # Propagate STOP reason from gate meta into run-level META (standardized enum).
        if result.decision == Decision.STOP and not self.meta.stop_reason:
            meta = result.meta or {}

            raw_reason = meta.get("stop_reason")
            raw_detail = meta.get("stop_detail") or meta.get("stop_error") or meta.get("error")

            if is_valid_stop_reason(raw_reason):
                self.meta.stop_reason = str(raw_reason)
            else:
                # Fallback to STOP_REQUESTED if gate didn't provide a valid code.
                self.meta.stop_reason = StopReason.STOP_REQUESTED.value
                # Preserve any provided detail for debugging.
                if isinstance(raw_reason, str) and raw_reason.strip():
                    raw_detail = raw_detail or raw_reason

            if isinstance(raw_detail, str) and raw_detail.strip():
                try:
                    self.meta.gate_metrics.setdefault(gate.value, {})["stop_detail"] = raw_detail.strip()
                except Exception:
                    pass

        next_gate = self._next_gate(gate, result.decision)
        self._record_transition(gate, next_gate, result.decision)

        self._steps_executed += 1
        return next_gate not in (GateId.DONE, GateId.STOP)

    def run(self) -> RunMeta:
        """Run until DONE or STOP."""
        self.meta.status = RunStatus.RUNNING
        if getattr(self.meta, "current_gate", None) in (None, GateId.DONE, GateId.STOP):
            self.meta.current_gate = GateId.G1
        try:
            while self.step():
                pass
            return self.meta
        finally:
            # Always persist run-level metadata for CLI / batch / future circuit execution.
            self._write_meta_json()