"""
circuit_runner.py

CircuitRunner — orchestrator for the CLI execution path:
  CLI → CircuitRunner → NodeExecutionRuntime

CircuitRunner owns circuit-level governance for this path using the same
governance module (ValidationDecisionPolicy) as Engine:

  Phase 1   — Structural pre-validation       (always blocking)
  Phase 1b  — Determinism pre-validation      (strict mode, blocking)
  Phase 2   — Node execution (DAG waves)
  Phase 3   — Determinism post-validation     (non-strict, advisory)
  Phase 4   — Trace finalization

Governance output:
  execute() returns CircuitRunResult(dict subclass).
  result["node_id"] works for all existing callers.
  result.governance carries a typed CircuitGovernanceTrace.
  Governance is NOT mixed into the dict namespace.

No-double-application:
  Engine.execute() delegates its governance phases to EngineGovernanceOrchestrator.
  CircuitRunner.execute() uses its own circuit-native structural validation
  + the same ValidationDecisionPolicy.
  The two paths share the policy module but not the validators.
  No path calls the other's governance. No double-application.
"""
from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
import re

from src.circuit.circuit_scheduler import CircuitScheduler
from src.circuit.circuit_validator import CircuitValidator, CircuitValidationError
from src.engine.validation.decision_policy import (
    PostDecisionResult,
    PreDecisionResult,
    ValidationDecisionPolicy,
)
from src.engine.validation.governance_shapes import (
    build_decision_block,
    build_post_validation_block,
    build_pre_validation_block,
    violations_as_dicts,
)
from src.engine.validation.result import (
    Severity,
    ValidationDecision,
    ValidationResult,
    Violation,
)


# ── Cross-node reference extraction ──────────────────────────────────────────

NODE_OUTPUT_REF_PATTERN = re.compile(
    r"^node\.(?P<node_id>[A-Za-z0-9_]+)\.output(?:\.[A-Za-z0-9_]+)*$"
)
NODE_OUTPUT_SHORTHAND_PATTERN = re.compile(
    r"^(?P<node_id>[A-Za-z0-9_]+)\.output(?:\.[A-Za-z0-9_]+)*$"
)


def _extract_cross_node_refs(value: Any) -> Set[str]:
    refs: Set[str] = set()
    if isinstance(value, str):
        m = NODE_OUTPUT_REF_PATTERN.match(value) or NODE_OUTPUT_SHORTHAND_PATTERN.match(value)
        if m:
            refs.add(m.group("node_id"))
        return refs
    if isinstance(value, dict):
        for v in value.values():
            refs.update(_extract_cross_node_refs(v))
        return refs
    if isinstance(value, list):
        for v in value:
            refs.update(_extract_cross_node_refs(v))
        return refs
    return refs


# ── Circuit governance trace ──────────────────────────────────────────────────

@dataclass
class CircuitGovernanceTrace:
    """
    Typed governance record for a single CircuitRunner execution.

    This is the architectural boundary for governance/trace output
    in the CircuitRunner path. It is NOT mixed into the execution state dict.

    The structure mirrors Engine's trace.meta governance blocks so that
    callers can reason about governance consistently across both paths.
    """

    execution_id: str
    circuit_id: Optional[str]

    # Phase 1 + 1b
    structural_success: bool
    structural_violations: List[Dict[str, Any]]
    determinism_pre_performed: bool       # True only in strict mode
    determinism_pre_success: bool
    determinism_pre_violations: List[Dict[str, Any]]

    # Pre-decision
    pre_decision: str                      # ValidationDecision.value
    pre_decision_reason: str
    execution_allowed: bool

    # Phase 3
    determinism_post_performed: bool       # True only in non-strict mode
    determinism_post_success: bool
    determinism_post_violations: List[Dict[str, Any]]

    # Post-decision + finalization
    post_decision: str                     # ValidationDecision.value
    post_decision_reason: str
    execution_completed: bool
    final_status: str                      # "success" | "blocked" | "failed"

    # Timing
    started_at_ms: float
    finished_at_ms: Optional[float] = None
    duration_ms: Optional[int] = None

    def to_engine_meta(self) -> Dict[str, Any]:
        structural = ValidationResult(
            success=self.structural_success,
            engine_revision="circuit",
            structural_fingerprint=_CIRCUIT_PATH_FINGERPRINT,
            violations=[],
        )
        structural = ValidationResult(
            success=self.structural_success,
            engine_revision=structural.engine_revision,
            structural_fingerprint=structural.structural_fingerprint,
            applied_rule_ids=structural.applied_rule_ids,
            violations=[
                Violation(
                    rule_id=v["rule_id"],
                    rule_name=v["rule_name"],
                    severity=Severity(v["severity"]),
                    location_type=v["location_type"],
                    location_id=v["location_id"],
                    message=v["message"],
                )
                for v in self.structural_violations
            ],
        )

        pre_det = None
        if self.determinism_pre_performed:
            pre_det = ValidationResult(
                success=self.determinism_pre_success,
                engine_revision="circuit",
                structural_fingerprint=_CIRCUIT_PATH_FINGERPRINT,
                violations=[
                    Violation(
                        rule_id=v["rule_id"],
                        rule_name=v["rule_name"],
                        severity=Severity(v["severity"]),
                        location_type=v["location_type"],
                        location_id=v["location_id"],
                        message=v["message"],
                    )
                    for v in self.determinism_pre_violations
                ],
            )

        post_det = None
        if self.determinism_post_performed:
            post_det = ValidationResult(
                success=self.determinism_post_success,
                engine_revision="circuit",
                structural_fingerprint=_CIRCUIT_PATH_FINGERPRINT,
                violations=[
                    Violation(
                        rule_id=v["rule_id"],
                        rule_name=v["rule_name"],
                        severity=Severity(v["severity"]),
                        location_type=v["location_type"],
                        location_id=v["location_id"],
                        message=v["message"],
                    )
                    for v in self.determinism_post_violations
                ],
            )

        return {
            "pre_validation": build_pre_validation_block(structural, pre_det),
            "post_validation": build_post_validation_block(
                post_det,
                strict_determinism=not self.determinism_post_performed,
            ),
            "decision": build_decision_block(
                pre_value=self.pre_decision,
                pre_reason=self.pre_decision_reason,
                post_value=self.post_decision,
                post_reason=self.post_decision_reason,
            ),
        }

    def to_dict(self) -> Dict[str, Any]:
        engine_meta = self.to_engine_meta()
        return {
            "execution_id": self.execution_id,
            "circuit_id": self.circuit_id,
            "pre_validation": engine_meta["pre_validation"],
            "pre_decision": {
                "value": self.pre_decision,
                "reason": self.pre_decision_reason,
                "execution_allowed": self.execution_allowed,
            },
            "post_validation": {
                "determinism": engine_meta["post_validation"],
            },
            "post_decision": {
                "value": self.post_decision,
                "reason": self.post_decision_reason,
            },
            "decision": engine_meta["decision"],
            "execution_completed": self.execution_completed,
            "final_status": self.final_status,
            "timing": {
                "started_at_ms": self.started_at_ms,
                "finished_at_ms": self.finished_at_ms,
                "duration_ms": self.duration_ms,
            },
        }


# ── CircuitRunResult ──────────────────────────────────────────────────────────

class CircuitRunResult(dict):
    """
    Return value of CircuitRunner.execute().

    IS a dict — result["node_id"] and all dict-based access works unchanged.
    HAS .governance — typed CircuitGovernanceTrace attribute.

    "governance" is NOT a key in the dict namespace. Governance is a separate
    typed boundary, not mixed into execution state.
    """

    def __init__(self, state: Dict[str, Any], governance: CircuitGovernanceTrace):
        super().__init__(state)
        self._governance = governance

    @property
    def governance(self) -> CircuitGovernanceTrace:
        return self._governance


# ── Helpers ───────────────────────────────────────────────────────────────────

_CIRCUIT_PATH_FINGERPRINT = "circuit-runner-path"


def _to_validation_result(violations: List[Violation], *, success: bool) -> ValidationResult:
    return ValidationResult(
        success=success,
        engine_revision="circuit",
        structural_fingerprint=_CIRCUIT_PATH_FINGERPRINT,
        applied_rule_ids=["CIRCUIT-STRUCTURAL"],
        violations=violations,
    )


# ── CircuitRunner ─────────────────────────────────────────────────────────────

class CircuitRunner:
    """
    Step140 — with governance lifecycle.

    Owns governance for the CLI execution path (CLI → CircuitRunner → NodeExecutionRuntime).

    Uses the same ValidationDecisionPolicy module as Engine.execute() (which now
    delegates to EngineGovernanceOrchestrator). No governance logic is duplicated.
    """

    def __init__(self, runtime, registry):
        self.runtime = runtime
        self.registry = registry
        self._policy = ValidationDecisionPolicy()

    def _build_governance_trace(
        self,
        *,
        execution_id: str,
        circuit_id: Optional[str],
        structural_result: ValidationResult,
        pre_det_result: Optional[ValidationResult],
        pre_decision: PreDecisionResult,
        execution_allowed: bool,
        post_det_result: Optional[ValidationResult],
        post_decision: PostDecisionResult,
        execution_completed: bool,
        final_status: str,
        started_at_ms: float,
        finished_at_ms: float,
    ) -> CircuitGovernanceTrace:
        return CircuitGovernanceTrace(
            execution_id=execution_id,
            circuit_id=circuit_id,
            structural_success=structural_result.success,
            structural_violations=violations_as_dicts(structural_result.violations),
            determinism_pre_performed=pre_det_result is not None,
            determinism_pre_success=(pre_det_result.success if pre_det_result else True),
            determinism_pre_violations=violations_as_dicts(
                pre_det_result.violations if pre_det_result else []
            ),
            pre_decision=pre_decision.decision.value,
            pre_decision_reason=pre_decision.reason,
            execution_allowed=execution_allowed,
            determinism_post_performed=post_det_result is not None,
            determinism_post_success=(post_det_result.success if post_det_result else True),
            determinism_post_violations=violations_as_dicts(
                post_det_result.violations if post_det_result else []
            ),
            post_decision=post_decision.decision.value,
            post_decision_reason=post_decision.reason,
            execution_completed=execution_completed,
            final_status=final_status,
            started_at_ms=started_at_ms,
            finished_at_ms=finished_at_ms,
            duration_ms=int((finished_at_ms - started_at_ms) * 1000),
        )

    def _emit_runtime_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        *,
        node_id: str = None,
    ) -> None:
        emit_fn = getattr(self.runtime, "_emit_event", None)
        if callable(emit_fn):
            emit_fn(event_type, payload, node_id=node_id)

    # ── Circuit-native structural validation ──────────────────────────────────

    def _run_structural_validation(self, circuit: Dict[str, Any]) -> ValidationResult:
        """
        Phase 1: Circuit-native structural pre-validation.

        Wraps CircuitValidator (duplicate IDs, missing deps, cycles, exec refs)
        and cross-node reference integrity into a ValidationResult so the
        shared ValidationDecisionPolicy can consume it uniformly.
        """
        violations: List[Violation] = []
        nodes = circuit.get("nodes", [])

        try:
            CircuitValidator(nodes).validate()
        except CircuitValidationError as exc:
            violations.append(
                Violation(
                    rule_id="CIRCUIT-STRUCTURAL",
                    rule_name="circuit structural validation",
                    severity=Severity.ERROR,
                    location_type="circuit",
                    location_id=None,
                    message=str(exc),
                )
            )

        if not violations:
            try:
                self._validate_cross_node_references(circuit)
            except ValueError as exc:
                violations.append(
                    Violation(
                        rule_id="CIRCUIT-CROSS-REF",
                        rule_name="circuit cross-node reference validation",
                        severity=Severity.ERROR,
                        location_type="circuit",
                        location_id=None,
                        message=str(exc),
                    )
                )

        return _to_validation_result(violations, success=len(violations) == 0)

    def _run_determinism_validation(
        self, circuit: Dict[str, Any], *, strict_determinism: bool = False
    ) -> ValidationResult:
        """
        Phase 1b / Phase 3: Circuit-native determinism validation.

        Note: Engine's DeterminismValidator uses Engine.meta.determinism and
        DET-001..007 rules. These are Engine-specific and cannot apply to the
        circuit path. Circuit-level determinism rules are not yet defined.

        The hook is fully wired: if violations are added, strict_determinism=True
        will produce BLOCK via ValidationDecisionPolicy. Contract is consistent.
        """
        det_severity = Severity.ERROR if strict_determinism else Severity.WARNING
        # No circuit-level determinism rules yet — always clean.
        return ValidationResult(
            success=True,
            engine_revision="circuit",
            structural_fingerprint=_CIRCUIT_PATH_FINGERPRINT,
            applied_rule_ids=["CIRCUIT-DETERMINISM"],
            violations=[],
        )

    # ── Cross-node reference check ────────────────────────────────────────────

    def _validate_cross_node_references(self, circuit: Dict[str, Any]) -> None:
        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])
        node_ids = {node.get("id") for node in nodes if node.get("id")}

        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                continue
            config_id = node.get("execution_config_ref")
            if not isinstance(config_id, str) or not config_id:
                continue
            config = self.registry.get(config_id)
            referenced_nodes = _extract_cross_node_refs(config)
            if not referenced_nodes:
                continue

            depends_on = set(node.get("depends_on", []))
            for rid in sorted(referenced_nodes):
                if rid == node_id:
                    raise ValueError(f"node cross-reference cannot target itself: {node_id}")
                if rid not in node_ids:
                    raise ValueError(
                        f"node cross-reference points to unknown node: {node_id} -> {rid}"
                    )
                if rid not in depends_on:
                    raise ValueError(
                        f"node cross-reference missing depends_on: {node_id} requires {rid}"
                    )

    # ── Node execution ────────────────────────────────────────────────────────

    def _execute_node(self, node: Dict[str, Any], state: Dict[str, Any]):
        if "execution_config_ref" not in node:
            raise ValueError(f"node missing execution_config_ref: {node.get('id')}")
        config_id = node["execution_config_ref"]
        result = self.runtime.execute_by_config_id(self.registry, config_id, state)
        return result.output

    def run_single_node(
        self,
        *,
        circuit: Dict[str, Any],
        node_id: str,
        state: Dict[str, Any],
    ):
        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])
        for node in nodes:
            if node.get("id") == node_id:
                return self._execute_node(node, state)
        raise ValueError(f"node not found in circuit: {node_id}")

    # ── Main execute ──────────────────────────────────────────────────────────

    def execute(
        self,
        circuit: Dict[str, Any],
        state: Dict[str, Any],
        *,
        strict_determinism: bool = False,
    ) -> CircuitRunResult:
        """
        Execute the circuit with full governance lifecycle.

        Phase 1   — Structural pre-validation  (always blocking)
        Phase 1b  — Determinism pre-validation (strict mode only, blocking)
        Phase 2   — Pre-decision: BLOCK → early return; CONTINUE → execute
        Phase 3   — Node execution (DAG waves via NodeExecutionRuntime)
        Phase 4   — Determinism post-validation (non-strict, advisory)
        Phase 5   — Post-decision + CircuitGovernanceTrace finalization

        Returns CircuitRunResult (dict subclass):
          - result["node_id"]  — node outputs (unchanged from original)
          - result.governance  — CircuitGovernanceTrace (typed governance boundary)
        """
        started_at_ms = time.monotonic()
        execution_id = str(uuid.uuid4())
        circuit_id = circuit.get("id")

        current_state: Dict[str, Any] = dict(state)
        current_state.setdefault("__node_outputs__", {})
        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])

        # ── Phase 1: Structural pre-validation ───────────────────────────────
        structural_result = self._run_structural_validation(circuit)

        # ── Phase 1b: Determinism pre-validation (strict mode only) ──────────
        pre_det_result: Optional[ValidationResult] = None
        if strict_determinism:
            pre_det_result = self._run_determinism_validation(
                circuit, strict_determinism=True
            )

        # ── Pre-decision application ──────────────────────────────────────────
        pre_decision: PreDecisionResult = self._policy.decide_pre(
            structural_result, pre_det_result
        )

        if pre_decision.blocks_execution:
            # Build blocked governance trace — no execution takes place
            finished_ms = time.monotonic()
            governance = self._build_governance_trace(
                execution_id=execution_id,
                circuit_id=circuit_id,
                structural_result=structural_result,
                pre_det_result=pre_det_result,
                pre_decision=pre_decision,
                execution_allowed=False,
                post_det_result=None,
                post_decision=PostDecisionResult(
                    decision=ValidationDecision.ACCEPT,
                    reason="execution blocked; no post-validation performed",
                ),
                execution_completed=False,
                final_status="blocked",
                started_at_ms=started_at_ms,
                finished_at_ms=finished_ms,
            )
            return CircuitRunResult(current_state, governance)

        # ── Phase 3: Node execution ───────────────────────────────────────────
        scheduler = CircuitScheduler(nodes)
        waves = scheduler.execution_waves()

        set_execution_id_fn = getattr(self.runtime, "set_execution_id", None)
        if callable(set_execution_id_fn):
            set_execution_id_fn(execution_id)

        self._emit_runtime_event(
            "execution_started",
            {
                "circuit_id": circuit_id,
                "execution_id": execution_id,
                "total_nodes": len(nodes),
                "total_waves": len(waves),
            },
        )

        execution_failed = False
        execution_error: Optional[Exception] = None
        executed_nodes_count = 0
        try:
            for wave_index, wave in enumerate(waves):
                with ThreadPoolExecutor() as executor:
                    futures = {}
                    for node_id in wave:
                        node = scheduler.nodes[node_id]
                        futures[node_id] = executor.submit(
                            self._execute_node, node, current_state
                        )
                    for node_id, future in futures.items():
                        node_output = future.result()
                        current_state[node_id] = node_output
                        executed_nodes_count += 1
                        node_outputs = current_state.setdefault("__node_outputs__", {})
                        if isinstance(node_outputs, dict):
                            node_outputs[node_id] = node_output
        except Exception as exc:
            execution_failed = True
            execution_error = exc
            raise
        finally:
            visible_keys = len([k for k in current_state if k != "__node_outputs__"])
            completed_event_type = "execution_failed" if execution_failed else "execution_completed"
            completed_payload = {
                "circuit_id": circuit_id,
                "execution_id": execution_id,
                "total_nodes": len(nodes),
                "total_waves": len(waves),
                "executed_nodes": executed_nodes_count,
                "state_keys": visible_keys,
            }
            if execution_error is not None:
                completed_payload["error"] = str(execution_error)
                completed_payload["error_type"] = type(execution_error).__name__

            self._emit_runtime_event(
                completed_event_type,
                completed_payload,
            )
            finished_ms = time.monotonic()

            # ── Phase 4: Determinism post-validation (advisory, non-strict) ───
            post_det_result: Optional[ValidationResult] = None
            if not strict_determinism:
                post_det_result = self._run_determinism_validation(
                    circuit, strict_determinism=False
                )

            # ── Phase 5: Post-decision + trace finalization ───────────────────
            post_decision: PostDecisionResult = self._policy.decide_post(
                post_det_result, strict_determinism=strict_determinism
            )
            if post_decision.decision is ValidationDecision.WARN:
                warning_count = len(post_det_result.violations) if post_det_result is not None else 0
                self._emit_runtime_event(
                    "warning",
                    {
                        "circuit_id": circuit_id,
                        "execution_id": execution_id,
                        "reason": post_decision.reason,
                        "warning_count": warning_count,
                    },
                )

            final_status = "failed" if execution_failed else "success"

            governance = self._build_governance_trace(
                execution_id=execution_id,
                circuit_id=circuit_id,
                structural_result=structural_result,
                pre_det_result=pre_det_result,
                pre_decision=pre_decision,
                execution_allowed=True,
                post_det_result=post_det_result,
                post_decision=post_decision,
                execution_completed=not execution_failed,
                final_status=final_status,
                started_at_ms=started_at_ms,
                finished_at_ms=finished_ms,
            )

        return CircuitRunResult(current_state, governance)
