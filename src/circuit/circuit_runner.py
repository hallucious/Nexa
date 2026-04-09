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

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import re

from src.automation.output_destination import (
    DeliveryAttempt,
    DeliveryPlan,
    DeliveryRecord,
    DestinationCapability,
    attempt_delivery,
    record_not_attempted_delivery,
)
from src.automation.trigger_model import DEFAULT_TRIGGER_SOURCE, normalize_trigger_source
from src.contracts.status_taxonomy import DeliveryStatus, GovernanceStatus, LaunchStatus
from src.governance.quota import (
    QuotaPolicy,
    QuotaScope,
    QuotaStateRecord,
    UsageAccountingRecord,
    apply_usage_accounting,
    evaluate_quota,
)
from src.safety.input_safety import evaluate_input_safety
from src.circuit.circuit_scheduler import CircuitScheduler
from src.circuit.circuit_validator import CircuitValidator, CircuitValidationError
from src.circuit.fingerprint import compute_circuit_fingerprint, compute_execution_surface_fingerprint
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
from src.engine.node_execution_runtime import ReviewRequiredPause
from src.engine.paused_run_state import PausedRunState, PausedRunStateError
from src.contracts.human_decision_contract import (
    DownstreamAction,
    HumanDecisionType,
    record_human_decision,
)
from src.engine.human_decision_registry import HumanDecisionRegistry
from src.contracts.branch_contract import MergePolicy, MergeResult, MergeStrategy


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


@dataclass(frozen=True)
class ReviewGateResumeRequest:
    """Minimal explicit resume contract for a paused review-gated run."""

    resume_from_node_id: str
    previous_execution_id: Optional[str] = None
    reason: str = "review_gate_resume"
    required_revalidation: Tuple[str, ...] = ()
    source_commit_id: Optional[str] = None
    structure_fingerprint: Optional[str] = None
    execution_surface_fingerprint: Optional[str] = None
    human_decision_record: Optional[Dict[str, Any]] = None
    merge_result_record: Optional[Dict[str, Any]] = None

    def to_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "resume_from_node_id": self.resume_from_node_id,
            "reason": self.reason,
        }
        if self.previous_execution_id:
            payload["previous_execution_id"] = self.previous_execution_id
        if self.required_revalidation:
            payload["requires_revalidation"] = list(self.required_revalidation)
        if self.source_commit_id:
            payload["source_commit_id"] = self.source_commit_id
        if self.structure_fingerprint:
            payload["structure_fingerprint"] = self.structure_fingerprint
        if self.execution_surface_fingerprint:
            payload["execution_surface_fingerprint"] = self.execution_surface_fingerprint
        if isinstance(self.human_decision_record, dict) and self.human_decision_record:
            payload["human_decision"] = dict(self.human_decision_record)
        if isinstance(self.merge_result_record, dict) and self.merge_result_record:
            payload["merge_result"] = dict(self.merge_result_record)
        return payload



_ALLOWED_RESUME_REVALIDATION_PHASES = frozenset({
    "structural_validation",
    "determinism_pre_validation",
})


def _normalize_required_revalidation(raw: Any) -> Tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise TypeError("resume requires_revalidation must be a list when provided")

    phases: list[str] = []
    seen: Set[str] = set()
    for item in raw:
        if not isinstance(item, str) or not item:
            raise TypeError("resume requires_revalidation entries must be non-empty strings")
        if item not in _ALLOWED_RESUME_REVALIDATION_PHASES:
            raise ValueError(
                f"unsupported resume revalidation phase: {item}; "
                f"allowed: {', '.join(sorted(_ALLOWED_RESUME_REVALIDATION_PHASES))}"
            )
        if item not in seen:
            phases.append(item)
            seen.add(item)
    return tuple(phases)


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
    final_status: str                      # "success" | "blocked" | "failed" | "paused"

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

    def __init__(
        self,
        state: Dict[str, Any],
        governance: CircuitGovernanceTrace,
        paused_run_state: Optional["PausedRunState"] = None,
    ):
        super().__init__(state)
        self._governance = governance
        self._paused_run_state = paused_run_state

    @property
    def governance(self) -> CircuitGovernanceTrace:
        return self._governance

    @property
    def paused_run_state(self) -> Optional["PausedRunState"]:
        """
        The persisted pause-state produced when execution was paused.

        None unless the run terminated with final_status == "paused".
        Callers may serialise this and pass it back via state["__paused_run_state__"]
        on resume to enable explicit structural drift detection.
        """
        return self._paused_run_state


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

    def __init__(self, runtime, registry, human_decision_registry: Optional[HumanDecisionRegistry] = None):
        self.runtime = runtime
        self.registry = registry
        self._policy = ValidationDecisionPolicy()
        self.human_decision_registry = human_decision_registry or getattr(runtime, "human_decision_registry", None)

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

    @staticmethod
    def _ensure_governance_store(state: Dict[str, Any]) -> Dict[str, Any]:
        governance = state.get("__governance__")
        if not isinstance(governance, dict):
            governance = {}
            state["__governance__"] = governance
        return governance

    @staticmethod
    def _refresh_governance_summary(current_state: Dict[str, Any]) -> Dict[str, Any]:
        governance = CircuitRunner._ensure_governance_store(current_state)
        summary = dict(governance.get("summary") or {})
        reason_codes: list[str] = []

        input_safety = governance.get("input_safety") if isinstance(governance.get("input_safety"), dict) else {}
        safety_decision = input_safety.get("decision") if isinstance(input_safety.get("decision"), dict) else {}
        safety_status = safety_decision.get("overall_status")
        if safety_status == "allow":
            summary["safety_status"] = "safe"
        elif safety_status == "allow_with_warning":
            summary["safety_status"] = "warning"
        elif safety_status == "confirmation_required":
            summary["safety_status"] = "confirmation_required"
        elif safety_status == "blocked":
            summary["safety_status"] = "blocked"
        safety_findings = input_safety.get("findings") if isinstance(input_safety.get("findings"), list) else []
        if safety_findings:
            codes = [str(item.get("reason_code")) for item in safety_findings if isinstance(item, dict) and item.get("reason_code")]
            if codes:
                summary["safety_reason_code"] = codes[0]
                reason_codes.extend(codes)

        quota_bundle = governance.get("quota") if isinstance(governance.get("quota"), dict) else {}
        quota_decision = quota_bundle.get("decision") if isinstance(quota_bundle.get("decision"), dict) else {}
        quota_status = quota_decision.get("overall_status")
        if quota_status == "blocked":
            summary["quota_status"] = "blocked"
        elif quota_status == "allow_with_warning":
            summary["quota_status"] = "near_limit"
        elif quota_status == "allow":
            summary["quota_status"] = "within_limit"
        if quota_decision.get("blocking_reason_code"):
            summary["quota_reason_code"] = quota_decision["blocking_reason_code"]
            reason_codes.append(str(quota_decision["blocking_reason_code"]))
        elif quota_decision.get("warning_summary"):
            summary["quota_reason_code"] = str(quota_decision["warning_summary"])
            reason_codes.append(str(quota_decision["warning_summary"]))

        delivery_bundle = governance.get("delivery") if isinstance(governance.get("delivery"), dict) else {}
        delivery_record = delivery_bundle.get("record") if isinstance(delivery_bundle.get("record"), dict) else {}
        delivery_attempt = delivery_bundle.get("attempt") if isinstance(delivery_bundle.get("attempt"), dict) else {}
        if delivery_record.get("latest_status"):
            summary["delivery_status"] = str(delivery_record.get("latest_status"))
        if delivery_record.get("destination_ref"):
            summary["delivery_destination_ref"] = str(delivery_record.get("destination_ref"))
        delivery_reason = delivery_attempt.get("failure_reason_code") or (delivery_record.get("delivery_summary") or {}).get("reason_code") if isinstance(delivery_record.get("delivery_summary"), dict) else None
        if delivery_reason:
            summary["delivery_reason_code"] = str(delivery_reason)
            reason_codes.append(str(delivery_reason))

        launch_status = governance.get("launch_status")
        if isinstance(launch_status, str) and launch_status:
            summary["launch_status"] = launch_status

        if reason_codes:
            unique: list[str] = []
            for code in reason_codes:
                if code not in unique:
                    unique.append(code)
            summary["reason_codes"] = unique
            summary["top_reason_code"] = unique[0]

        governance["summary"] = summary
        return summary

    def _maybe_evaluate_input_safety(
        self,
        current_state: Dict[str, Any],
        *,
        trigger_source: str,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        raw = current_state.get("__input_safety__")
        if not isinstance(raw, dict):
            return None

        evaluation = evaluate_input_safety(
            raw.get("inputs") or [],
            trigger_source=trigger_source,
            confirmed_by=raw.get("confirmed_by"),
            confirmed_at=raw.get("confirmed_at"),
        )
        governance = self._ensure_governance_store(current_state)
        governance["input_safety"] = evaluation
        raw["evaluation"] = evaluation
        self._refresh_governance_summary(current_state)

        decision = dict(evaluation.get("decision") or {})
        payload = {
            "execution_id": execution_id,
            "overall_status": decision.get("overall_status"),
            "launch_allowed": bool(decision.get("launch_allowed")),
            "finding_count": len(evaluation.get("findings") or []),
            "finding_reason_codes": [finding.get("reason_code") for finding in evaluation.get("findings") or []],
            "governance_status": GovernanceStatus.INPUT_SAFE.value if decision.get("overall_status") == "allow" else (
                GovernanceStatus.INPUT_WARNING.value if decision.get("overall_status") == "allow_with_warning" else (
                    GovernanceStatus.CONFIRMATION_REQUIRED.value if decision.get("overall_status") == "confirmation_required" else GovernanceStatus.INPUT_BLOCKED.value
                )
            ),
        }
        self._emit_runtime_event("input_safety_evaluated", payload)
        if not decision.get("launch_allowed"):
            event_type = "input_safety_confirmation_required" if decision.get("overall_status") == "confirmation_required" else "input_safety_blocked"
            self._emit_runtime_event(event_type, payload)
        return evaluation

    def _resolve_quota_components(self, current_state: Dict[str, Any]) -> Optional[Tuple[Dict[str, Any], QuotaScope, QuotaPolicy, QuotaStateRecord]]:
        raw = current_state.get("__quota__")
        if not isinstance(raw, dict):
            return None
        scope = QuotaScope.from_raw(dict(raw.get("scope") or {}))
        policy = QuotaPolicy.from_raw(dict(raw.get("policy") or {}), scope_ref=scope.scope_ref)
        period_ref = str(raw.get("period_ref") or f"{policy.period_type}:default")
        state_record = QuotaStateRecord.from_raw(dict(raw.get("state_record") or {}), scope_ref=scope.scope_ref, period_ref=period_ref)
        return raw, scope, policy, state_record

    def _maybe_evaluate_quota(
        self,
        current_state: Dict[str, Any],
        *,
        trigger_source: str,
        execution_id: str,
        requested_action_type: Optional[str] = None,
        estimated_usage: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        resolved = self._resolve_quota_components(current_state)
        if resolved is None:
            return None
        raw, scope, policy, state_record = resolved
        action_type = requested_action_type or str(raw.get("requested_action_type") or ("automation_launch" if trigger_source != DEFAULT_TRIGGER_SOURCE else "run_launch"))
        usage = dict(estimated_usage or raw.get("estimated_usage") or {"run_count": 1})
        decision = evaluate_quota(
            scope=scope,
            policy=policy,
            state_record=state_record,
            requested_action_type=action_type,
            estimated_usage=usage,
        )
        payload = {
            "execution_id": execution_id,
            "scope_ref": scope.scope_ref,
            "requested_action_type": action_type,
            "overall_status": decision.overall_status,
            "blocking_reason_code": decision.blocking_reason_code,
            "warning_summary": decision.warning_summary,
            "governance_status": GovernanceStatus.OVER_QUOTA_BLOCKED.value if decision.overall_status == "blocked" else (
                GovernanceStatus.NEAR_QUOTA.value if decision.overall_status == "allow_with_warning" else GovernanceStatus.WITHIN_QUOTA.value
            ),
        }
        self._emit_runtime_event("quota_evaluated", payload)
        if decision.overall_status == "blocked":
            self._emit_runtime_event("quota_blocked", payload)
        elif decision.overall_status == "allow_with_warning":
            self._emit_runtime_event("quota_warning", payload)

        bundle = {
            "scope": scope.to_dict(),
            "policy": policy.to_dict(),
            "state_record": state_record.to_dict(),
            "decision": decision.to_dict(),
        }
        governance = self._ensure_governance_store(current_state)
        governance["quota"] = bundle
        raw["evaluation"] = bundle
        self._refresh_governance_summary(current_state)
        return bundle

    def _apply_quota_accounting(
        self,
        current_state: Dict[str, Any],
        *,
        run_ref: str,
        action_type: str,
        estimated_cost: Optional[float] = None,
        delivery_actions_used: Optional[int] = None,
        automation_launches_used: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        resolved = self._resolve_quota_components(current_state)
        if resolved is None:
            return None
        raw, _scope, _policy, state_record = resolved
        accounting = UsageAccountingRecord(
            accounting_id=str(uuid.uuid4()),
            scope_ref=state_record.scope_ref,
            run_ref=run_ref,
            action_type=action_type,
            estimated_cost=estimated_cost,
            delivery_actions_used=delivery_actions_used,
            automation_launches_used=automation_launches_used,
        )
        updated_state = apply_usage_accounting(state_record=state_record, accounting=accounting)
        raw["state_record"] = updated_state.to_dict()
        governance = self._ensure_governance_store(current_state)
        quota_governance = governance.setdefault("quota", {})
        quota_governance["state_record"] = updated_state.to_dict()
        accounting_records = quota_governance.setdefault("accounting_records", [])
        accounting_records.append(accounting.to_dict())
        self._refresh_governance_summary(current_state)
        return {
            "accounting": accounting.to_dict(),
            "state_record": updated_state.to_dict(),
        }

    def _maybe_attempt_output_delivery(
        self,
        current_state: Dict[str, Any],
        *,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        raw = current_state.get("__delivery__")
        if not isinstance(raw, dict):
            return None

        capability = DestinationCapability.from_raw(dict(raw.get("capability") or {}))
        plan = DeliveryPlan.from_raw(dict(raw.get("plan") or raw), run_ref=execution_id)
        outputs = dict(current_state.get("__node_outputs__") or {})
        if not outputs:
            outputs = {key: value for key, value in current_state.items() if isinstance(key, str) and not key.startswith("__")}
        artifacts = dict(raw.get("artifacts") or {})
        authorization_allowed = bool(raw.get("authorization_allowed", True))
        confirmation_granted = bool(raw.get("confirmation_granted", False))

        quota_bundle = self._maybe_evaluate_quota(
            current_state,
            trigger_source=DEFAULT_TRIGGER_SOURCE,
            execution_id=execution_id,
            requested_action_type="delivery_action",
            estimated_usage={"delivery_actions": 1},
        )
        if quota_bundle is not None and dict(quota_bundle.get("decision") or {}).get("overall_status") == "blocked":
            blocked_attempt = {
                "attempt_id": str(uuid.uuid4()),
                "delivery_plan_ref": plan.delivery_plan_id,
                "run_ref": execution_id,
                "destination_ref": plan.destination_ref,
                "started_at": None,
                "completed_at": None,
                "status": DeliveryStatus.BLOCKED.value,
                "idempotency_key": None,
                "response_summary": None,
                "failure_reason_code": dict(quota_bundle["decision"]).get("blocking_reason_code"),
                "retry_eligible": False,
            }
            record = DeliveryRecord(
                run_ref=execution_id,
                destination_ref=plan.destination_ref,
                destination_type=plan.destination_type,
                selected_output_ref=plan.selected_output_ref,
                selected_artifact_ref=plan.selected_artifact_ref,
                latest_status=DeliveryStatus.BLOCKED.value,
                attempt_refs=(blocked_attempt["attempt_id"],),
                delivered_at=None,
                delivery_summary={"reason_code": blocked_attempt["failure_reason_code"]},
            ).to_dict()
            result = {"attempt": blocked_attempt, "record": record, "payload": None}
        else:
            result = attempt_delivery(
                capability=capability,
                plan=plan,
                outputs=outputs,
                artifacts=artifacts,
                authorization_allowed=authorization_allowed,
                confirmation_granted=confirmation_granted,
            )

        raw["last_result"] = result
        governance = self._ensure_governance_store(current_state)
        governance["delivery"] = result
        self._refresh_governance_summary(current_state)
        latest_status = dict(result.get("record") or {}).get("latest_status", DeliveryStatus.UNKNOWN.value if hasattr(DeliveryStatus, 'UNKNOWN') else 'unknown')
        event_type = {
            DeliveryStatus.SUCCEEDED.value: "delivery_succeeded",
            DeliveryStatus.FAILED.value: "delivery_failed",
            DeliveryStatus.BLOCKED.value: "delivery_blocked",
            DeliveryStatus.CANCELLED.value: "delivery_cancelled",
        }.get(latest_status, "delivery_recorded")
        self._emit_runtime_event(
            event_type,
            {
                "execution_id": execution_id,
                "destination_ref": plan.destination_ref,
                "destination_type": plan.destination_type,
                "latest_status": latest_status,
                "attempt_id": dict(result.get("attempt") or {}).get("attempt_id"),
                "failure_reason_code": dict(result.get("attempt") or {}).get("failure_reason_code"),
            },
        )
        if latest_status in {DeliveryStatus.SUCCEEDED.value, DeliveryStatus.FAILED.value, DeliveryStatus.BLOCKED.value}:
            self._apply_quota_accounting(
                current_state,
                run_ref=execution_id,
                action_type="delivery_action",
                delivery_actions_used=1,
            )
        return result


    def _build_resume_human_decision_record(
        self,
        raw: Any,
        *,
        resume_from_node_id: str,
        previous_execution_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise TypeError("__resume__.human_decision must be a dict when provided")

        decision_type = raw.get("decision_type")
        actor_ref = raw.get("actor_ref")
        if not isinstance(decision_type, str) or not decision_type:
            raise ValueError("__resume__.human_decision.decision_type must be a non-empty string")
        if not isinstance(actor_ref, str) or not actor_ref:
            raise ValueError("__resume__.human_decision.actor_ref must be a non-empty string")

        allowed_types = {
            HumanDecisionType.APPROVE: DownstreamAction.CONTINUE,
            HumanDecisionType.OVERRIDE_WITH_REASON: DownstreamAction.CONTINUE,
            HumanDecisionType.REQUEST_REVISION: DownstreamAction.RERUN,
            HumanDecisionType.CHOOSE_BRANCH: DownstreamAction.BRANCH,
            HumanDecisionType.CHOOSE_MERGE: DownstreamAction.MERGE,
        }
        if decision_type not in allowed_types:
            raise ValueError(
                "resume human_decision decision_type must be one of: "
                + ", ".join(sorted(allowed_types))
            )

        rationale_text = raw.get("rationale_text")
        if rationale_text is not None and not isinstance(rationale_text, str):
            raise TypeError("__resume__.human_decision.rationale_text must be a string when provided")
        selected_option_ref = raw.get("selected_option_ref")
        if selected_option_ref is not None and not isinstance(selected_option_ref, str):
            raise TypeError("__resume__.human_decision.selected_option_ref must be a string when provided")

        trace_refs: List[str] = []
        if isinstance(previous_execution_id, str) and previous_execution_id:
            trace_refs.append(f"trace://{previous_execution_id}#node:{resume_from_node_id}")

        record = record_human_decision(
            target_ref=f"node.{resume_from_node_id}.review_gate",
            decision_type=decision_type,
            actor_ref=actor_ref,
            downstream_action=allowed_types[decision_type],
            trace_refs=trace_refs,
            rationale_text=rationale_text,
            selected_option_ref=selected_option_ref,
        )

        if isinstance(self.human_decision_registry, HumanDecisionRegistry):
            self.human_decision_registry.register(record)

        return record.to_dict()

    def _build_resume_merge_result_record(
        self,
        raw: Any,
        *,
        resume_from_node_id: str,
        previous_execution_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, dict):
            return None

        decision_type = raw.get("decision_type")
        if decision_type not in {HumanDecisionType.CHOOSE_BRANCH, HumanDecisionType.CHOOSE_MERGE}:
            return None

        selected_option_ref = raw.get("selected_option_ref")
        if not isinstance(selected_option_ref, str) or not selected_option_ref:
            return None

        candidate_branch_ids = raw.get("candidate_branch_ids")
        if not isinstance(candidate_branch_ids, list):
            return None
        normalized_candidate_ids: List[str] = []
        for item in candidate_branch_ids:
            if not isinstance(item, str) or not item:
                raise TypeError("__resume__.human_decision.candidate_branch_ids entries must be non-empty strings")
            if item not in normalized_candidate_ids:
                normalized_candidate_ids.append(item)
        if len(normalized_candidate_ids) < 2:
            return None
        if selected_option_ref not in normalized_candidate_ids:
            raise ValueError("__resume__.human_decision.selected_option_ref must be present in candidate_branch_ids")

        policy = MergePolicy(
            policy_id="review_gate_human_merge",
            strategy=MergeStrategy.HUMAN_CHOICE,
            conflict_action="escalate",
            require_human_on_tie=False,
        )
        discarded = [branch_id for branch_id in normalized_candidate_ids if branch_id != selected_option_ref]
        explanation = (
            f"review_gate_human_merge selected={selected_option_ref}; "
            f"discarded={len(discarded)}; source={resume_from_node_id}"
        )
        result = MergeResult(
            merge_id=str(uuid.uuid4()),
            selected_branch_id=selected_option_ref,
            discarded_branch_ids=discarded,
            merge_policy=policy,
            conflict_detected=False,
            requires_human_decision=False,
            merged_artifact_refs=[],
            explanation=explanation,
        )
        payload = {
            "merge_result": result.to_dict(),
            "target_ref": f"node.{resume_from_node_id}.review_gate",
            "decision_type": decision_type,
            "selected_option_ref": selected_option_ref,
            "candidate_branch_ids": normalized_candidate_ids,
            "previous_execution_id": previous_execution_id,
        }
        return payload

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

    # ── Review-gate resume helpers ─────────────────────────────────────────────

    def _extract_resume_request(
        self,
        state: Dict[str, Any],
        circuit_nodes: Optional[List[Dict[str, Any]]] = None,
        circuit_definition: Optional[Dict[str, Any]] = None,
    ) -> Optional[ReviewGateResumeRequest]:
        """
        Extract and validate a resume request from execution state.

        If state contains ``__paused_run_state__`` (a serialised PausedRunState
        dict), it is loaded and validated against the current circuit before
        the resume is permitted.  This is the explicit stale/invalid-state
        rejection contract.

        The ``__resume__`` key is always consumed (popped) regardless of whether
        a paused_run_state is also present.  ``__paused_run_state__`` is also
        consumed so it does not pollute working state.
        """
        # Extract optional persisted pause state first (consume before __resume__)
        raw_prs = state.pop("__paused_run_state__", None)
        persisted: Optional[PausedRunState] = None
        if raw_prs is not None:
            if not isinstance(raw_prs, dict):
                raise TypeError("state['__paused_run_state__'] must be a dict when provided")
            try:
                persisted = PausedRunState.from_dict(raw_prs)
            except PausedRunStateError as exc:
                raise ValueError(f"cannot load persisted paused run state: {exc}") from exc
            # Validate structural integrity against the current circuit
            if circuit_nodes is not None:
                persisted.validate_for_resume(circuit_nodes)

        raw = state.pop("__resume__", None)

        # If a persisted pause state is present but no __resume__ was provided,
        # reject explicitly.  Auto-deriving the resume target would hide the
        # caller's intent and make the boundary less observable.
        if persisted is not None and raw is None:
            raise ValueError(
                "__paused_run_state__ was provided but __resume__ is absent; "
                "supply __resume__ with resume_from_node_id to proceed"
            )

        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise TypeError("state['__resume__'] must be a dict when provided")

        resume_from_node_id = raw.get("resume_from_node_id") or raw.get("pause_node_id")
        if not isinstance(resume_from_node_id, str) or not resume_from_node_id:
            raise ValueError("resume request requires non-empty resume_from_node_id")

        # Enforce durable boundary: __resume__.resume_from_node_id must exactly
        # match the persisted paused_node_id.  A mismatch means the caller is
        # attempting to resume from a different node than the one that was paused,
        # which violates the durable boundary contract.
        if persisted is not None and resume_from_node_id != persisted.paused_node_id:
            raise ValueError(
                f"resume_from_node_id '{resume_from_node_id}' does not match "
                f"persisted paused_node_id '{persisted.paused_node_id}'; "
                "resume must restart from the node recorded in the paused run state"
            )

        previous_execution_id = raw.get("previous_execution_id")
        if previous_execution_id is not None and not isinstance(previous_execution_id, str):
            raise TypeError("previous_execution_id must be a string when provided")

        source_commit_id = raw.get("source_commit_id")
        if source_commit_id is not None and not isinstance(source_commit_id, str):
            raise TypeError("source_commit_id must be a string when provided")

        structure_fingerprint = raw.get("structure_fingerprint")
        if structure_fingerprint is not None and not isinstance(structure_fingerprint, str):
            raise TypeError("structure_fingerprint must be a string when provided")

        execution_surface_fingerprint = raw.get("execution_surface_fingerprint")
        if execution_surface_fingerprint is not None and not isinstance(execution_surface_fingerprint, str):
            raise TypeError("execution_surface_fingerprint must be a string when provided")
        if isinstance(execution_surface_fingerprint, str) and not execution_surface_fingerprint:
            raise ValueError("execution_surface_fingerprint must be non-empty when provided")

        current_structure_fingerprint = None
        current_execution_surface_fingerprint = None
        if circuit_definition is not None:
            current_structure_fingerprint = compute_circuit_fingerprint(circuit_definition)
            current_execution_surface_fingerprint = compute_execution_surface_fingerprint(circuit_definition)

        required_revalidation = _normalize_required_revalidation(raw.get("requires_revalidation"))
        if persisted is not None:
            if not persisted.source_commit_id:
                raise ValueError(
                    "persisted paused run state is missing source_commit_id; "
                    "resume is not allowed without a stored source commit anchor"
                )
            if not source_commit_id:
                raise ValueError(
                    "__resume__ is missing source_commit_id; "
                    "resume is not allowed without a resume source commit anchor"
                )
            if not persisted.execution_surface_fingerprint:
                raise ValueError(
                    "persisted paused run state is missing execution_surface_fingerprint; "
                    "resume is not allowed without an execution-surface fingerprint"
                )
            if not execution_surface_fingerprint:
                raise ValueError(
                    "__resume__ is missing execution_surface_fingerprint; "
                    "resume is not allowed without an execution-surface fingerprint"
                )

            persisted_required_revalidation = tuple(persisted.required_revalidation)
            if required_revalidation and required_revalidation != persisted_required_revalidation:
                raise ValueError(
                    "resume requires_revalidation does not match persisted paused run state; "
                    "resume must use the revalidation requirements recorded in paused_run_state"
                )
            required_revalidation = persisted_required_revalidation

            persisted_source_commit_id = persisted.source_commit_id
            if persisted_source_commit_id and source_commit_id and source_commit_id != persisted_source_commit_id:
                raise ValueError(
                    "resume source_commit_id does not match persisted paused run state; "
                    "resume must use the commit anchor recorded in paused_run_state"
                )
            source_commit_id = persisted_source_commit_id or source_commit_id

            persisted_structure_fingerprint = persisted.structure_fingerprint
            if persisted_structure_fingerprint and structure_fingerprint and structure_fingerprint != persisted_structure_fingerprint:
                raise ValueError(
                    "resume structure_fingerprint does not match persisted paused run state; "
                    "resume must use the structural fingerprint recorded in paused_run_state"
                )
            structure_fingerprint = persisted_structure_fingerprint or structure_fingerprint

            persisted_execution_surface_fingerprint = persisted.execution_surface_fingerprint
            if (
                persisted_execution_surface_fingerprint
                and execution_surface_fingerprint
                and execution_surface_fingerprint != persisted_execution_surface_fingerprint
            ):
                raise ValueError(
                    "resume execution_surface_fingerprint does not match persisted paused run state; "
                    "resume must use the execution-surface fingerprint recorded in paused_run_state"
                )
            execution_surface_fingerprint = (
                persisted_execution_surface_fingerprint or execution_surface_fingerprint
            )

        if current_structure_fingerprint and structure_fingerprint and current_structure_fingerprint != structure_fingerprint:
            raise ValueError(
                "current circuit structure_fingerprint does not match paused run state; "
                "resume is not allowed across structurally drifted drafts"
            )

        if persisted is not None and not current_execution_surface_fingerprint:
            raise ValueError(
                "current circuit execution_surface_fingerprint is missing; "
                "resume is not allowed without a current execution-surface fingerprint"
            )

        if (
            current_execution_surface_fingerprint
            and execution_surface_fingerprint
            and current_execution_surface_fingerprint != execution_surface_fingerprint
        ):
            raise ValueError(
                "current circuit execution_surface_fingerprint does not match paused run state; "
                "resume is not allowed across execution-surface drift"
            )

        # If a persisted paused run state was also provided, use its execution ID
        # as the authoritative prior-run linkage (overrides __resume__ field).
        if persisted is not None and not previous_execution_id:
            previous_execution_id = persisted.paused_execution_id

        reason = raw.get("reason") or "review_gate_resume"
        if not isinstance(reason, str):
            raise TypeError("resume reason must be a string when provided")

        human_decision_record = self._build_resume_human_decision_record(
            raw.get("human_decision"),
            resume_from_node_id=resume_from_node_id,
            previous_execution_id=previous_execution_id,
        )

        merge_result_record = self._build_resume_merge_result_record(
            raw.get("human_decision"),
            resume_from_node_id=resume_from_node_id,
            previous_execution_id=previous_execution_id,
        )

        return ReviewGateResumeRequest(
            resume_from_node_id=resume_from_node_id,
            previous_execution_id=previous_execution_id,
            reason=reason,
            required_revalidation=required_revalidation,
            source_commit_id=source_commit_id,
            structure_fingerprint=structure_fingerprint or current_structure_fingerprint,
            execution_surface_fingerprint=(
                execution_surface_fingerprint or current_execution_surface_fingerprint
            ),
            human_decision_record=human_decision_record,
            merge_result_record=merge_result_record,
        )

    def _build_resume_nodes(
        self,
        nodes: List[Dict[str, Any]],
        state: Dict[str, Any],
        resume_request: ReviewGateResumeRequest,
    ) -> List[Dict[str, Any]]:
        node_map = {node.get("id"): node for node in nodes if node.get("id")}
        if resume_request.resume_from_node_id not in node_map:
            raise ValueError(f"resume target node not found in circuit: {resume_request.resume_from_node_id}")

        node_outputs = state.get("__node_outputs__")
        if not isinstance(node_outputs, dict):
            raise ValueError("resume execution requires state['__node_outputs__'] dict")

        completed_nodes = {node_id for node_id in node_outputs if isinstance(node_id, str) and node_id}
        completed_nodes.discard(resume_request.resume_from_node_id)

        resume_node = node_map[resume_request.resume_from_node_id]
        missing_deps = [
            dep for dep in resume_node.get("depends_on", [])
            if dep not in completed_nodes
        ]
        if missing_deps:
            raise ValueError(
                "resume execution requires completed dependency outputs for "
                f"{resume_request.resume_from_node_id}: missing {', '.join(sorted(missing_deps))}"
            )

        resume_nodes: List[Dict[str, Any]] = []
        for node in nodes:
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                continue
            if node_id in completed_nodes:
                continue
            cloned = dict(node)
            cloned["depends_on"] = [
                dep for dep in node.get("depends_on", [])
                if dep not in completed_nodes
            ]
            resume_nodes.append(cloned)

        return resume_nodes

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
        trigger_source: str = DEFAULT_TRIGGER_SOURCE,
        automation_id: Optional[str] = None,
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
        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])
        resume_request = self._extract_resume_request(current_state, circuit_nodes=nodes, circuit_definition=circuit)
        current_state.setdefault("__node_outputs__", {})
        normalized_trigger_source = normalize_trigger_source(trigger_source)
        governance_store = self._ensure_governance_store(current_state)
        governance_store.setdefault("launch_status", LaunchStatus.REQUESTED.value)

        # ── Phase 1: Structural pre-validation ───────────────────────────────
        structural_result = self._run_structural_validation(circuit)

        # ── Phase 1b: Determinism pre-validation (strict mode only) ──────────
        pre_det_result: Optional[ValidationResult] = None
        should_run_determinism_pre = bool(
            strict_determinism
            or (
                resume_request is not None
                and "determinism_pre_validation" in resume_request.required_revalidation
            )
        )
        if should_run_determinism_pre:
            pre_det_result = self._run_determinism_validation(
                circuit, strict_determinism=True
            )

        # ── Pre-decision application ──────────────────────────────────────────
        pre_decision: PreDecisionResult = self._policy.decide_pre(
            structural_result, pre_det_result
        )

        if pre_decision.blocks_execution:
            governance_store["launch_status"] = LaunchStatus.BLOCKED.value
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

        safety_bundle = self._maybe_evaluate_input_safety(
            current_state,
            trigger_source=normalized_trigger_source,
            execution_id=execution_id,
        )
        if safety_bundle is not None and not dict(safety_bundle.get("decision") or {}).get("launch_allowed"):
            governance_store["launch_status"] = (
                LaunchStatus.CONFIRMATION_REQUIRED.value
                if dict(safety_bundle.get("decision") or {}).get("overall_status") == "confirmation_required"
                else LaunchStatus.SAFETY_BLOCKED.value
            )
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
                    reason="execution blocked by input safety",
                ),
                execution_completed=False,
                final_status="blocked",
                started_at_ms=started_at_ms,
                finished_at_ms=finished_ms,
            )
            return CircuitRunResult(current_state, governance)

        quota_bundle = self._maybe_evaluate_quota(
            current_state,
            trigger_source=normalized_trigger_source,
            execution_id=execution_id,
        )
        if quota_bundle is not None and dict(quota_bundle.get("decision") or {}).get("overall_status") == "blocked":
            governance_store["launch_status"] = LaunchStatus.QUOTA_BLOCKED.value
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
                    reason="execution blocked by quota",
                ),
                execution_completed=False,
                final_status="blocked",
                started_at_ms=started_at_ms,
                finished_at_ms=finished_ms,
            )
            return CircuitRunResult(current_state, governance)

        governance_store["launch_status"] = LaunchStatus.ALLOWED.value

        # ── Phase 3: Node execution ───────────────────────────────────────────
        execution_nodes = nodes if resume_request is None else self._build_resume_nodes(nodes, current_state, resume_request)
        scheduler = CircuitScheduler(execution_nodes)
        waves = scheduler.execution_waves()

        set_execution_identity_fn = getattr(self.runtime, "set_execution_identity", None)
        if callable(set_execution_identity_fn):
            set_execution_identity_fn(
                execution_id=execution_id,
                trigger_source=normalized_trigger_source,
                automation_id=automation_id,
            )
        else:
            set_execution_id_fn = getattr(self.runtime, "set_execution_id", None)
            if callable(set_execution_id_fn):
                set_execution_id_fn(execution_id)

        started_payload = {
            "circuit_id": circuit_id,
            "execution_id": execution_id,
            "total_nodes": len(execution_nodes),
            "total_nodes_in_circuit": len(nodes),
            "total_waves": len(waves),
            "is_resume": resume_request is not None,
            "trigger_source": normalized_trigger_source,
            "launch_status": governance_store.get("launch_status", LaunchStatus.ALLOWED.value),
        }
        if automation_id is not None:
            started_payload["automation_id"] = automation_id

        if resume_request is not None:
            started_payload["resume_from_node_id"] = resume_request.resume_from_node_id
            if resume_request.previous_execution_id:
                started_payload["previous_execution_id"] = resume_request.previous_execution_id

        self._emit_runtime_event("execution_started", started_payload)
        if resume_request is not None:
            self._emit_runtime_event("execution_resumed", resume_request.to_payload())
            if isinstance(resume_request.human_decision_record, dict):
                self._emit_runtime_event(
                    "human_decision_recorded",
                    dict(resume_request.human_decision_record),
                    node_id=resume_request.resume_from_node_id,
                )
            if isinstance(resume_request.merge_result_record, dict):
                self._emit_runtime_event(
                    "merge_result_declared",
                    dict(resume_request.merge_result_record),
                    node_id=resume_request.resume_from_node_id,
                )

        execution_failed = False
        execution_error: Optional[Exception] = None
        execution_paused = False
        pause_signal: Optional[ReviewRequiredPause] = None
        executed_nodes_count = 0
        produced_paused_run_state: Optional[PausedRunState] = None
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
        except ReviewRequiredPause as exc:
            execution_paused = True
            pause_signal = exc
        except Exception as exc:
            execution_failed = True
            execution_error = exc
            raise
        finally:
            visible_keys = len([k for k in current_state if not (isinstance(k, str) and k.startswith("__"))])
            if execution_paused:
                completed_event_type = "execution_paused"
            else:
                completed_event_type = "execution_failed" if execution_failed else "execution_completed"
            completed_payload = {
                "circuit_id": circuit_id,
                "execution_id": execution_id,
                "total_nodes": len(nodes),
                "total_waves": len(waves),
                "executed_nodes": executed_nodes_count,
                "state_keys": visible_keys,
                "trigger_source": normalized_trigger_source,
            }
            if automation_id is not None:
                completed_payload["automation_id"] = automation_id
            if execution_error is not None:
                completed_payload["error"] = str(execution_error)
                completed_payload["error_type"] = type(execution_error).__name__
            if pause_signal is not None:
                completed_payload["reason"] = str(pause_signal.payload.get("reason") or "review_required")
                completed_payload["review_required"] = dict(pause_signal.payload)
                completed_payload["resume"] = {
                    "can_resume": True,
                    "resume_from_node_id": pause_signal.node_id,
                    "resume_strategy": "restart_from_node",
                    "requires_revalidation": ["structural_validation", "determinism_pre_validation"],
                    "previous_execution_id": execution_id,
                }
                completed_payload["pause_node_id"] = pause_signal.node_id

            self._emit_runtime_event(
                completed_event_type,
                completed_payload,
            )
            finished_ms = time.monotonic()

            # ── Phase 4: Determinism post-validation (advisory, non-strict) ───
            post_det_result: Optional[ValidationResult] = None
            if not should_run_determinism_pre and not execution_paused:
                post_det_result = self._run_determinism_validation(
                    circuit, strict_determinism=False
                )

            # ── Phase 5: Post-decision + trace finalization ───────────────────
            if execution_paused:
                post_decision = PostDecisionResult(
                    decision=ValidationDecision.ACCEPT,
                    reason="execution paused; no post-validation performed",
                )
            else:
                post_decision = self._policy.decide_post(
                    post_det_result, strict_determinism=strict_determinism
                )
            if (not execution_paused) and post_decision.decision is ValidationDecision.WARN:
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

            launch_action_type = "automation_launch" if normalized_trigger_source != DEFAULT_TRIGGER_SOURCE else "run_launch"
            self._apply_quota_accounting(
                current_state,
                run_ref=execution_id,
                action_type=launch_action_type,
                estimated_cost=(dict(current_state.get("__quota__") or {}).get("estimated_usage") or {}).get("estimated_cost"),
                automation_launches_used=(1 if launch_action_type == "automation_launch" else None),
            )

            if execution_paused or execution_failed:
                raw_delivery = current_state.get("__delivery__")
                if isinstance(raw_delivery, dict):
                    plan = DeliveryPlan.from_raw(dict(raw_delivery.get("plan") or raw_delivery), run_ref=execution_id)
                    delivery_result = {"attempt": None, "record": record_not_attempted_delivery(plan=plan).to_dict(), "payload": None}
                    raw_delivery["last_result"] = delivery_result
                    governance_store["delivery"] = delivery_result
                    self._emit_runtime_event(
                        "delivery_recorded",
                        {
                            "execution_id": execution_id,
                            "destination_ref": plan.destination_ref,
                            "destination_type": plan.destination_type,
                            "latest_status": DeliveryStatus.NOT_ATTEMPTED.value,
                            "attempt_id": None,
                            "failure_reason_code": None,
                        },
                    )
            else:
                self._maybe_attempt_output_delivery(current_state, execution_id=execution_id)

            final_status = "paused" if execution_paused else ("failed" if execution_failed else "success")

            # ── Build persisted pause-state on pause ──────────────────────────
            produced_paused_run_state: Optional[PausedRunState] = None
            if execution_paused and pause_signal is not None:
                node_outputs = current_state.get("__node_outputs__") or {}
                completed = frozenset(
                    nid for nid in node_outputs
                    if isinstance(nid, str) and nid != pause_signal.node_id
                )
                produced_paused_run_state = PausedRunState.build(
                    paused_execution_id=execution_id,
                    paused_node_id=pause_signal.node_id,
                    completed_node_ids=completed,
                    review_required=dict(pause_signal.payload),
                    previous_execution_id=(
                        resume_request.previous_execution_id if resume_request else None
                    ),
                    structure_fingerprint=compute_circuit_fingerprint(circuit),
                    execution_surface_fingerprint=compute_execution_surface_fingerprint(circuit),
                )

            governance = self._build_governance_trace(
                execution_id=execution_id,
                circuit_id=circuit_id,
                structural_result=structural_result,
                pre_det_result=pre_det_result,
                pre_decision=pre_decision,
                execution_allowed=True,
                post_det_result=post_det_result,
                post_decision=post_decision,
                execution_completed=(not execution_failed and not execution_paused),
                final_status=final_status,
                started_at_ms=started_at_ms,
                finished_at_ms=finished_ms,
            )

        return CircuitRunResult(current_state, governance, paused_run_state=produced_paused_run_state)


    # ── Async execution path ──────────────────────────────────────────────────

    async def _execute_node_async(
        self, node: Dict[str, Any], state: Dict[str, Any]
    ):
        """Async counterpart to _execute_node.

        Delegates to NodeExecutionRuntime.execute_async() which uses
        asyncio.gather() internally for same-wave resource concurrency.
        I/O-bound work (provider HTTP calls, plugin execution) is offloaded
        via asyncio.to_thread() so the event loop is never blocked.
        """
        if "execution_config_ref" not in node:
            raise ValueError(f"node missing execution_config_ref: {node.get('id')}")
        config_id = node["execution_config_ref"]
        # Resolve config from registry synchronously (cheap CPU work)
        config = self.registry.get(config_id)
        if not isinstance(config, dict):
            raise TypeError("execution config registry must return dict config")
        result = await self.runtime.execute_async(config, state)
        return result.output

    async def execute_async(
        self,
        circuit: Dict[str, Any],
        state: Dict[str, Any],
        *,
        strict_determinism: bool = False,
        trigger_source: str = DEFAULT_TRIGGER_SOURCE,
        automation_id: Optional[str] = None,
    ) -> "CircuitRunResult":
        """True async execution path for a circuit.

        Same governance lifecycle as execute() but the node execution phase
        (Phase 3) uses asyncio.gather() to run same-wave nodes concurrently.

        Wave ordering is preserved: wave N+1 begins only after all tasks in
        wave N have resolved.

        Usage
        -----
        result = await runner.execute_async(circuit, state)

        Or from sync context (no running loop):
            result = asyncio.run(runner.execute_async(circuit, state))
        """
        started_at_ms = time.monotonic()
        execution_id = str(uuid.uuid4())
        circuit_id = circuit.get("id")

        current_state: Dict[str, Any] = dict(state)
        nodes: List[Dict[str, Any]] = circuit.get("nodes", [])
        resume_request = self._extract_resume_request(
            current_state, circuit_nodes=nodes, circuit_definition=circuit
        )
        current_state.setdefault("__node_outputs__", {})
        normalized_trigger_source = normalize_trigger_source(trigger_source)
        governance_store = self._ensure_governance_store(current_state)
        governance_store.setdefault("launch_status", LaunchStatus.REQUESTED.value)

        # ── Phase 1: Structural pre-validation ───────────────────────────────
        structural_result = self._run_structural_validation(circuit)

        # ── Phase 1b: Determinism pre-validation (strict mode only) ──────────
        pre_det_result: Optional[ValidationResult] = None
        should_run_determinism_pre = bool(
            strict_determinism
            or (
                resume_request is not None
                and "determinism_pre_validation" in resume_request.required_revalidation
            )
        )
        if should_run_determinism_pre:
            pre_det_result = self._run_determinism_validation(
                circuit, strict_determinism=True
            )

        # ── Pre-decision ──────────────────────────────────────────────────────
        pre_decision: PreDecisionResult = self._policy.decide_pre(
            structural_result, pre_det_result
        )

        if pre_decision.blocks_execution:
            governance_store["launch_status"] = LaunchStatus.BLOCKED.value
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

        safety_bundle = self._maybe_evaluate_input_safety(
            current_state,
            trigger_source=normalized_trigger_source,
            execution_id=execution_id,
        )
        if safety_bundle is not None and not dict(safety_bundle.get("decision") or {}).get("launch_allowed"):
            governance_store["launch_status"] = (
                LaunchStatus.CONFIRMATION_REQUIRED.value
                if dict(safety_bundle.get("decision") or {}).get("overall_status") == "confirmation_required"
                else LaunchStatus.SAFETY_BLOCKED.value
            )
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
                    reason="execution blocked by input safety",
                ),
                execution_completed=False,
                final_status="blocked",
                started_at_ms=started_at_ms,
                finished_at_ms=finished_ms,
            )
            return CircuitRunResult(current_state, governance)

        quota_bundle = self._maybe_evaluate_quota(
            current_state,
            trigger_source=normalized_trigger_source,
            execution_id=execution_id,
        )
        if quota_bundle is not None and dict(quota_bundle.get("decision") or {}).get("overall_status") == "blocked":
            governance_store["launch_status"] = LaunchStatus.QUOTA_BLOCKED.value
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
                    reason="execution blocked by quota",
                ),
                execution_completed=False,
                final_status="blocked",
                started_at_ms=started_at_ms,
                finished_at_ms=finished_ms,
            )
            return CircuitRunResult(current_state, governance)

        governance_store["launch_status"] = LaunchStatus.ALLOWED.value

        # ── Phase 3: Node execution (async wave loop) ─────────────────────────
        execution_nodes = (
            nodes if resume_request is None
            else self._build_resume_nodes(nodes, current_state, resume_request)
        )
        scheduler = CircuitScheduler(execution_nodes)
        waves = scheduler.execution_waves()

        set_execution_identity_fn = getattr(self.runtime, "set_execution_identity", None)
        if callable(set_execution_identity_fn):
            set_execution_identity_fn(
                execution_id=execution_id,
                trigger_source=normalized_trigger_source,
                automation_id=automation_id,
            )
        else:
            set_execution_id_fn = getattr(self.runtime, "set_execution_id", None)
            if callable(set_execution_id_fn):
                set_execution_id_fn(execution_id)

        started_payload = {
            "circuit_id": circuit_id,
            "execution_id": execution_id,
            "total_nodes": len(execution_nodes),
            "total_nodes_in_circuit": len(nodes),
            "total_waves": len(waves),
            "is_resume": resume_request is not None,
            "execution_mode": "async",
            "trigger_source": normalized_trigger_source,
            "launch_status": governance_store.get("launch_status", LaunchStatus.ALLOWED.value),
        }
        if automation_id is not None:
            started_payload["automation_id"] = automation_id
        if resume_request is not None:
            started_payload["resume_from_node_id"] = resume_request.resume_from_node_id
            if resume_request.previous_execution_id:
                started_payload["previous_execution_id"] = resume_request.previous_execution_id

        self._emit_runtime_event("execution_started", started_payload)
        if resume_request is not None:
            self._emit_runtime_event("execution_resumed", resume_request.to_payload())
            if isinstance(resume_request.human_decision_record, dict):
                self._emit_runtime_event(
                    "human_decision_recorded",
                    dict(resume_request.human_decision_record),
                    node_id=resume_request.resume_from_node_id,
                )
            if isinstance(resume_request.merge_result_record, dict):
                self._emit_runtime_event(
                    "merge_result_declared",
                    dict(resume_request.merge_result_record),
                    node_id=resume_request.resume_from_node_id,
                )

        execution_failed = False
        execution_error: Optional[Exception] = None
        execution_paused = False
        pause_signal: Optional[ReviewRequiredPause] = None
        executed_nodes_count = 0
        produced_paused_run_state: Optional[PausedRunState] = None

        try:
            for wave in waves:
                if len(wave) == 1:
                    # Single node: run directly without gather overhead
                    node_id = wave[0]
                    node = scheduler.nodes[node_id]
                    node_output = await self._execute_node_async(node, current_state)
                    current_state[node_id] = node_output
                    executed_nodes_count += 1
                    node_outputs = current_state.setdefault("__node_outputs__", {})
                    if isinstance(node_outputs, dict):
                        node_outputs[node_id] = node_output
                else:
                    # Multiple nodes in this wave: run concurrently via asyncio.gather
                    async def _run_one(nid: str) -> tuple:
                        n = scheduler.nodes[nid]
                        output = await self._execute_node_async(n, current_state)
                        return nid, output

                    wave_results = await asyncio.gather(*[_run_one(nid) for nid in wave])
                    for node_id, node_output in wave_results:
                        current_state[node_id] = node_output
                        executed_nodes_count += 1
                        node_outputs = current_state.setdefault("__node_outputs__", {})
                        if isinstance(node_outputs, dict):
                            node_outputs[node_id] = node_output

        except ReviewRequiredPause as exc:
            execution_paused = True
            pause_signal = exc
        except Exception as exc:
            execution_failed = True
            execution_error = exc
            raise
        finally:
            visible_keys = len([k for k in current_state if not (isinstance(k, str) and k.startswith("__"))])
            if execution_paused:
                completed_event_type = "execution_paused"
            else:
                completed_event_type = "execution_failed" if execution_failed else "execution_completed"
            completed_payload = {
                "circuit_id": circuit_id,
                "execution_id": execution_id,
                "total_nodes": len(nodes),
                "total_waves": len(waves),
                "executed_nodes": executed_nodes_count,
                "state_keys": visible_keys,
                "execution_mode": "async",
                "trigger_source": normalized_trigger_source,
            }
            if automation_id is not None:
                completed_payload["automation_id"] = automation_id
            if execution_error is not None:
                completed_payload["error"] = str(execution_error)
                completed_payload["error_type"] = type(execution_error).__name__
            if pause_signal is not None:
                completed_payload["reason"] = str(
                    pause_signal.payload.get("reason") or "review_required"
                )
                completed_payload["review_required"] = dict(pause_signal.payload)
                completed_payload["resume"] = {
                    "can_resume": True,
                    "resume_from_node_id": pause_signal.node_id,
                    "resume_strategy": "restart_from_node",
                    "requires_revalidation": [
                        "structural_validation",
                        "determinism_pre_validation",
                    ],
                    "previous_execution_id": execution_id,
                }
                completed_payload["pause_node_id"] = pause_signal.node_id
            self._emit_runtime_event(completed_event_type, completed_payload)

        # ── Phase 4: Determinism post-validation ──────────────────────────────
        if not execution_failed and not execution_paused:
            post_det_result = self._run_determinism_validation(
                circuit, strict_determinism=False
            )
        else:
            post_det_result = None

        post_decision = self._policy.decide_post(
            post_det_result, strict_determinism=strict_determinism
        )

        launch_action_type = "automation_launch" if normalized_trigger_source != DEFAULT_TRIGGER_SOURCE else "run_launch"
        self._apply_quota_accounting(
            current_state,
            run_ref=execution_id,
            action_type=launch_action_type,
            estimated_cost=(dict(current_state.get("__quota__") or {}).get("estimated_usage") or {}).get("estimated_cost"),
            automation_launches_used=(1 if launch_action_type == "automation_launch" else None),
        )

        if execution_paused or execution_failed:
            raw_delivery = current_state.get("__delivery__")
            if isinstance(raw_delivery, dict):
                plan = DeliveryPlan.from_raw(dict(raw_delivery.get("plan") or raw_delivery), run_ref=execution_id)
                delivery_result = {"attempt": None, "record": record_not_attempted_delivery(plan=plan).to_dict(), "payload": None}
                raw_delivery["last_result"] = delivery_result
                governance_store["delivery"] = delivery_result
                self._emit_runtime_event(
                    "delivery_recorded",
                    {
                        "execution_id": execution_id,
                        "destination_ref": plan.destination_ref,
                        "destination_type": plan.destination_type,
                        "latest_status": DeliveryStatus.NOT_ATTEMPTED.value,
                        "attempt_id": None,
                        "failure_reason_code": None,
                    },
                )
        else:
            self._maybe_attempt_output_delivery(current_state, execution_id=execution_id)

        final_status = (
            "paused" if execution_paused
            else ("failed" if execution_failed else "success")
        )

        finished_ms = time.monotonic()

        if execution_paused and pause_signal is not None:
            completed = set(
                nid for nid in current_state
                if isinstance(nid, str) and nid != pause_signal.node_id
            )
            produced_paused_run_state = PausedRunState.build(
                paused_execution_id=execution_id,
                paused_node_id=pause_signal.node_id,
                completed_node_ids=completed,
                review_required=dict(pause_signal.payload),
                previous_execution_id=(
                    resume_request.previous_execution_id if resume_request else None
                ),
                structure_fingerprint=compute_circuit_fingerprint(circuit),
                execution_surface_fingerprint=compute_execution_surface_fingerprint(circuit),
            )

        governance = self._build_governance_trace(
            execution_id=execution_id,
            circuit_id=circuit_id,
            structural_result=structural_result,
            pre_det_result=pre_det_result,
            pre_decision=pre_decision,
            execution_allowed=True,
            post_det_result=post_det_result,
            post_decision=post_decision,
            execution_completed=(not execution_failed and not execution_paused),
            final_status=final_status,
            started_at_ms=started_at_ms,
            finished_at_ms=finished_ms,
        )

        return CircuitRunResult(
            current_state, governance, paused_run_state=produced_paused_run_state
        )
