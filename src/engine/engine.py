from __future__ import annotations
from src.utils.time import now_utc, now_utc_iso

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

from src.contracts.runtime_contract_versions import (
    ENGINE_EXECUTION_MODEL_VERSION,
    ENGINE_TRACE_MODEL_VERSION,
    VALIDATION_ENGINE_CONTRACT_VERSION,
    VALIDATION_RULE_CATALOG_VERSION,
)

from .fingerprint import StructuralFingerprint, compute_fingerprint
from .model import Channel, EngineStructure, FlowRule
from .revision import Revision
from .trace import ExecutionTrace, NodeTrace
from .types import FlowPolicy, NodeFailurePolicy, NodeStatus, StageStatus
from .node_execution_runtime import NodeExecutionRuntime
from .graph_execution_runtime import GraphExecutionRuntime


# Handler signatures for v1.5 execution (Step48):
# - Core handler: input_snapshot -> output_snapshot
# - Pipeline handler: dict with optional "pre"/"core"/"post" callables
CoreHandler = Callable[[Dict[str, Any]], Dict[str, Any]]
PreHandler = Callable[[Dict[str, Any]], Dict[str, Any]]
PostHandler = Callable[[Dict[str, Any]], Dict[str, Any]]

NodeHandler = CoreHandler  # backward-compatible alias

def _is_staged_handler(obj: Any) -> bool:
    return isinstance(obj, dict) and any(k in obj for k in ("pre", "core", "post"))

@dataclass
class RetryConfig:
    """Configuration for node-level retry (v1).

    Attributes:
        max_attempts: Total execution attempts allowed (must be >= 1).
                      max_attempts=1 is equivalent to no retry.
    """
    max_attempts: int  # >= 1


@dataclass
class Engine:
    entry_node_id: str
    node_ids: List[str]
    channels: List[Channel] = field(default_factory=list)
    flow: List[FlowRule] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    # Node execution handlers (optional).
    # If a node is reached but no handler is registered, the engine uses a default no-op handler.
    handlers: Dict[str, Union[NodeHandler, Dict[str, Any]]] = field(default_factory=dict, repr=False)

    # Optional execution kernel (Step116+): if provided, the engine can delegate node execution.
    node_runtime: Optional[NodeExecutionRuntime] = field(default=None, repr=False)

    # Optional graph runtime (Step117+): if provided, Engine can delegate graph traversal.
    graph_runtime: Optional[GraphExecutionRuntime] = field(default=None, repr=False)

    # Per-node failure propagation policy (default: STRICT for all nodes).
    # Controls how upstream FAILURE affects a downstream node.
    # Nodes not listed here are treated as STRICT (current default behavior).
    node_failure_policies: Dict[str, NodeFailurePolicy] = field(default_factory=dict, repr=False)

    # Per-node fallback map: if a node fails, attempt its fallback once.
    # key: primary node_id  →  value: fallback_node_id
    # Constraints (v1):
    #   - single fallback only (no chaining)
    #   - fallback executes at most once with the same input_snapshot
    #   - fallback does NOT affect DAG structure / edges
    node_fallback_map: Dict[str, str] = field(default_factory=dict, repr=False)

    # Per-node retry policy (default: single execution, no retry).
    # key: node_id  →  RetryConfig with max_attempts
    # Constraints:
    #   - same input_snapshot for all attempts
    #   - stops immediately on first SUCCESS
    #   - retry runs BEFORE fallback (primary → retry → fallback)
    node_retry_policy: Dict[str, "RetryConfig"] = field(default_factory=dict, repr=False)

    def to_structure(self) -> EngineStructure:
        return EngineStructure(
            entry_node_id=self.entry_node_id,
            node_ids=list(self.node_ids),
            channels=list(self.channels),
            flow=list(self.flow),
            meta=dict(self.meta),
        )

    def fingerprint(self) -> StructuralFingerprint:
        return compute_fingerprint(self.to_structure())

    def make_revision(self, *, revision_id: str, meta: Optional[Dict[str, Any]] = None) -> Revision:
        fp = self.fingerprint()
        return Revision(revision_id=revision_id, fingerprint=fp, meta=meta or {})

    def _build_graph(self) -> Dict[str, List[str]]:
        graph: Dict[str, List[str]] = {nid: [] for nid in self.node_ids}
        for ch in self.channels:
            if ch.src_node_id in graph and ch.dst_node_id in graph:
                graph[ch.src_node_id].append(ch.dst_node_id)
        return graph

    def _build_reverse_graph(self) -> Dict[str, List[str]]:
        reverse: Dict[str, List[str]] = {nid: [] for nid in self.node_ids}
        for ch in self.channels:
            if ch.src_node_id in reverse and ch.dst_node_id in reverse:
                reverse[ch.dst_node_id].append(ch.src_node_id)
        return reverse

    def _noop_handler(self, _input: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def _apply_retry(
        self,
        node_id: str,
        input_snapshot: Dict[str, Any],
    ) -> NodeTrace:
        """Execute a node with optional retry, then return the final NodeTrace.

        Execution order: attempt 1 → attempt 2 … → attempt max_attempts.
        Stops immediately on first SUCCESS.
        If all attempts fail, returns the last FAILURE trace.

        Retry meta is attached only when max_attempts > 1:
            node.meta["retry"] = {
                "attempted": True,
                "attempt_count": <total attempts made>,
                "final_attempt": <0-based index of final attempt>,
                "history": [{"attempt": i, "status": "SUCCESS"|"FAILURE"}, ...]
            }

        Edge cases:
            - No policy configured   → single execution, no retry meta.
            - max_attempts = 1       → single execution, no retry meta.
            - max_attempts < 1       → immediate FAILURE (config error).
            - Same input_snapshot used for every attempt (no mutation).
        """
        cfg = self.node_retry_policy.get(node_id)
        max_attempts = cfg.max_attempts if cfg is not None else 1

        # Config error: max_attempts < 1
        if max_attempts < 1:
            return NodeTrace(
                node_id=node_id,
                node_status=NodeStatus.FAILURE,
                pre_status=StageStatus.SKIPPED,
                core_status=StageStatus.SKIPPED,
                post_status=StageStatus.SKIPPED,
                reason_code="ENG-RETRY-INVALID-CONFIG",
                message=f"node '{node_id}' RetryConfig.max_attempts must be >= 1, got {max_attempts}",
                input_snapshot=dict(input_snapshot),
                output_snapshot=None,
            )

        history: List[Dict[str, Any]] = []
        last_trace: Optional[NodeTrace] = None

        for attempt in range(max_attempts):
            trace = self._run_node(node_id=node_id, input_snapshot=dict(input_snapshot))
            status_str = "SUCCESS" if trace.node_status == NodeStatus.SUCCESS else "FAILURE"
            history.append({"attempt": attempt, "status": status_str})
            last_trace = trace

            if trace.node_status == NodeStatus.SUCCESS:
                break  # stop immediately on first success

        assert last_trace is not None  # loop always executes at least once

        # Attach retry meta only when max_attempts > 1
        if max_attempts > 1:
            existing_meta = dict(last_trace.meta) if last_trace.meta else {}
            existing_meta["retry"] = {
                "attempted": True,
                "attempt_count": len(history),
                "final_attempt": history[-1]["attempt"],
                "history": history,
            }
            last_trace = NodeTrace(
                node_id=last_trace.node_id,
                node_status=last_trace.node_status,
                pre_status=last_trace.pre_status,
                core_status=last_trace.core_status,
                post_status=last_trace.post_status,
                reason_code=last_trace.reason_code,
                message=last_trace.message,
                input_snapshot=last_trace.input_snapshot,
                output_snapshot=last_trace.output_snapshot,
                meta=existing_meta,
            )

        return last_trace

    def _apply_fallback(
        self,
        node_id: str,
        original_trace: NodeTrace,
        input_snapshot: Dict[str, Any],
    ) -> NodeTrace:
        """Attempt a single fallback execution if a fallback is configured for node_id.

        Called only when the primary node resulted in FAILURE.

        Rules (v1):
        - Single fallback, executed at most once.
        - Fallback receives the same input_snapshot as the original node.
        - Fallback does NOT affect DAG edges or upstream visibility.
        - If fallback == original node, treat as config error (prevent loop).
        - If fallback_node_id not in node_ids, treat as config error → FAILURE.
        - If fallback succeeds, replace the original trace with the fallback result
          and embed recovery metadata.
        - If fallback fails, keep FAILURE and embed recovery metadata.

        Returns:
            The final NodeTrace to use for this node (either recovered or still failed).
        """
        fallback_node_id = self.node_fallback_map.get(node_id)
        if fallback_node_id is None:
            # No fallback configured; return original failure unchanged.
            return original_trace

        # Edge case: fallback == original node (prevent infinite loop).
        if fallback_node_id == node_id:
            return NodeTrace(
                node_id=node_id,
                node_status=NodeStatus.FAILURE,
                pre_status=original_trace.pre_status,
                core_status=original_trace.core_status,
                post_status=original_trace.post_status,
                reason_code="ENG-FALLBACK-SELF-REF",
                message=f"fallback node_id must differ from primary node_id '{node_id}'",
                input_snapshot=original_trace.input_snapshot,
                output_snapshot=None,
                meta=dict(original_trace.meta) if original_trace.meta else None,
            )

        # Edge case: fallback_node_id not registered in node_ids.
        if fallback_node_id not in set(self.node_ids):
            return NodeTrace(
                node_id=node_id,
                node_status=NodeStatus.FAILURE,
                pre_status=original_trace.pre_status,
                core_status=original_trace.core_status,
                post_status=original_trace.post_status,
                reason_code="ENG-FALLBACK-UNKNOWN-NODE",
                message=(
                    f"fallback node '{fallback_node_id}' for '{node_id}' "
                    "is not registered in engine node_ids"
                ),
                input_snapshot=original_trace.input_snapshot,
                output_snapshot=None,
                meta=dict(original_trace.meta) if original_trace.meta else None,
            )

        # Execute fallback (same input, single attempt).
        fallback_trace = self._run_node(
            node_id=fallback_node_id,
            input_snapshot=dict(input_snapshot),
        )

        # Build recovery metadata block.
        recovery_meta: Dict[str, Any] = {
            "recovery": {
                "used": True,
                "fallback_node": fallback_node_id,
                "original_failure": {
                    "reason_code": original_trace.reason_code,
                    "message": original_trace.message,
                },
            }
        }

        # Merge with existing node meta (if any).
        if fallback_trace.node_status == NodeStatus.SUCCESS:
            # Fallback succeeded — replace the original failure.
            existing_meta = dict(fallback_trace.meta) if fallback_trace.meta else {}
            existing_meta.update(recovery_meta)
            return NodeTrace(
                node_id=node_id,           # keep original node_id for DAG consistency
                node_status=NodeStatus.SUCCESS,
                pre_status=fallback_trace.pre_status,
                core_status=fallback_trace.core_status,
                post_status=fallback_trace.post_status,
                reason_code=None,
                message=None,
                input_snapshot=fallback_trace.input_snapshot,
                output_snapshot=fallback_trace.output_snapshot,
                meta=existing_meta,
            )
        else:
            # Fallback also failed — keep FAILURE, record recovery attempt.
            existing_meta = dict(original_trace.meta) if original_trace.meta else {}
            existing_meta["recovery"] = {
                "used": True,
                "fallback_node": fallback_node_id,
                "original_failure": {
                    "reason_code": original_trace.reason_code,
                    "message": original_trace.message,
                },
                "fallback_failure": {
                    "reason_code": fallback_trace.reason_code,
                    "message": fallback_trace.message,
                },
            }
            return NodeTrace(
                node_id=node_id,
                node_status=NodeStatus.FAILURE,
                pre_status=original_trace.pre_status,
                core_status=original_trace.core_status,
                post_status=original_trace.post_status,
                reason_code=original_trace.reason_code,
                message=original_trace.message,
                input_snapshot=original_trace.input_snapshot,
                output_snapshot=None,
                meta=existing_meta,
            )


    def _run_node(self, *, node_id: str, input_snapshot: Dict[str, Any]) -> NodeTrace:
        """Run node using pre / core / post stages.

        Backward compatible:
        - If handlers[node_id] is a callable: treated as Core handler.
        - If handlers[node_id] is a dict with pre/core/post: staged handler (pre/core/post dict).

        Node-level validation runs BEFORE handler dispatch:
        - NodeValidator.validate(...) → NodeValidationResult
        - NodeDecisionPolicy.decide(...) → NodeDecisionOutcome
        - If decision is FAIL: handler is not executed; node is marked FAILURE.
        - Validation outcome is recorded in node.meta.
        """
        from .validation.node_validator import NodeValidator
        from .validation.node_decision_policy import NodeDecisionPolicy

        # ── Node-level validation (always before handler) ─────────────────────
        _node_validator = NodeValidator()
        _node_decision_policy = NodeDecisionPolicy()

        node_val_result = _node_validator.validate(
            node_id=node_id,
            input_snapshot=dict(input_snapshot),
            context=None,
        )
        node_decision_outcome = _node_decision_policy.decide(node_val_result)

        # Build node-level validation metadata (attached to NodeTrace.meta)
        _node_meta: Dict[str, Any] = {
            "validation": {
                "performed": True,
                "success": node_val_result.success,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "severity": v.severity.value,
                        "location_type": v.location_type,
                        "location_id": v.location_id,
                        "message": v.message,
                    }
                    for v in node_val_result.violations
                ],
            },
            "decision": {
                "value": node_decision_outcome.decision.value,
                "reason": node_decision_outcome.reason,
            },
        }

        # If node validation decided FAIL → block handler; mark node FAILURE.
        if node_decision_outcome.blocks_execution:
            return NodeTrace(
                node_id=node_id,
                node_status=NodeStatus.FAILURE,
                pre_status=StageStatus.SKIPPED,
                core_status=StageStatus.SKIPPED,
                post_status=StageStatus.SKIPPED,
                reason_code="NODE-VALIDATION-FAIL",
                message=node_decision_outcome.reason,
                input_snapshot=dict(input_snapshot),
                output_snapshot=None,
                meta=_node_meta,
            )

        # ── Handler dispatch ───────────────────────────────────────────────────
        handler_obj = self.handlers.get(node_id)

        # Step116+: if no explicit handler is registered and a node runtime is provided,
        # delegate execution to the runtime.
        if handler_obj is None and self.node_runtime is not None:
            try:
                runtime_result = self.node_runtime.execute(
                    node={"config_id": node_id, "node_id": node_id},
                    state=dict(input_snapshot),
                )
                out = runtime_result.output
                output_snapshot: Optional[Dict[str, Any]]
                if isinstance(out, dict):
                    output_snapshot = dict(out)
                else:
                    output_snapshot = {"output": out}

                return NodeTrace(
                    node_id=node_id,
                    node_status=NodeStatus.SUCCESS,
                    pre_status=StageStatus.SKIPPED,
                    core_status=StageStatus.SUCCESS,
                    post_status=StageStatus.SKIPPED,
                    reason_code=None,
                    message=None,
                    input_snapshot=dict(input_snapshot),
                    output_snapshot=output_snapshot,
                    meta=_node_meta,
                )
            except Exception as e:
                return NodeTrace(
                    node_id=node_id,
                    node_status=NodeStatus.FAILURE,
                    pre_status=StageStatus.SKIPPED,
                    core_status=StageStatus.FAILURE,
                    post_status=StageStatus.SKIPPED,
                    reason_code="ENG-RUNTIME-EXC",
                    message=str(e),
                    input_snapshot=dict(input_snapshot),
                    output_snapshot=None,
                    meta=_node_meta,
                )

        pre_fn: Optional[PreHandler] = None
        core_fn: Optional[CoreHandler] = None
        post_fn: Optional[PostHandler] = None

        if handler_obj is None:
            core_fn = self._noop_handler
        elif callable(handler_obj):
            core_fn = handler_obj  # type: ignore[assignment]
        elif _is_staged_handler(handler_obj):
            pre_fn = handler_obj.get("pre")
            core_fn = handler_obj.get("core") or self._noop_handler
            post_fn = handler_obj.get("post")
        else:
            return NodeTrace(
                node_id=node_id,
                node_status=NodeStatus.FAILURE,
                pre_status=StageStatus.FAILURE,
                core_status=StageStatus.SKIPPED,
                post_status=StageStatus.SKIPPED,
                reason_code="ENG-HANDLER-CONFIG",
                message=f"invalid handler config for {node_id}",
                input_snapshot=dict(input_snapshot),
                output_snapshot=None,
                meta=_node_meta,
            )

        pre_status = StageStatus.SUCCESS
        core_status = StageStatus.SKIPPED
        post_status = StageStatus.SKIPPED

        final_input = dict(input_snapshot)
        reason_code: Optional[str] = None
        message: Optional[str] = None

        # Pre
        try:
            if pre_fn is not None:
                pre_out = pre_fn(dict(final_input))
                if pre_out is None:
                    pre_out = {}
                if not isinstance(pre_out, dict):
                    raise TypeError(f"pre output must be dict, got {type(pre_out).__name__}")
                final_input = dict(pre_out)
        except Exception as e:
            pre_status = StageStatus.FAILURE
            reason_code = "ENG-PRE-EXC"
            message = str(e)

        core_output: Optional[Dict[str, Any]] = None

        # Core (only if Pre succeeded)
        if pre_status == StageStatus.SUCCESS:
            try:
                out_dict = core_fn(dict(final_input)) if core_fn is not None else {}
                if out_dict is None:
                    out_dict = {}
                if not isinstance(out_dict, dict):
                    raise TypeError(f"core output must be dict, got {type(out_dict).__name__}")
                core_output = dict(out_dict)
                core_status = StageStatus.SUCCESS
            except Exception as e:
                core_status = StageStatus.FAILURE
                reason_code = reason_code or "ENG-CORE-EXC"
                message = message or str(e)

        # Post (always runs)
        final_output: Optional[Dict[str, Any]] = core_output
        try:
            ctx = {
                "input": dict(final_input),
                "core_output": dict(core_output) if core_output is not None else None,
                "pre_status": pre_status.value,
                "core_status": core_status.value,
            }
            if post_fn is not None:
                post_out = post_fn(ctx)
                if post_out is None:
                    post_out = {}
                if not isinstance(post_out, dict):
                    raise TypeError(f"post output must be dict, got {type(post_out).__name__}")
                final_output = dict(post_out)
            post_status = StageStatus.SUCCESS
        except Exception as e:
            post_status = StageStatus.FAILURE
            reason_code = reason_code or "ENG-POST-EXC"
            message = message or str(e)
            final_output = None

        node_success = (
            pre_status == StageStatus.SUCCESS
            and core_status == StageStatus.SUCCESS
            and post_status == StageStatus.SUCCESS
        )
        node_status = NodeStatus.SUCCESS if node_success else NodeStatus.FAILURE

        return NodeTrace(
            node_id=node_id,
            node_status=node_status,
            pre_status=pre_status,
            core_status=core_status,
            post_status=post_status,
            reason_code=reason_code,
            message=message,
            input_snapshot=dict(final_input),
            output_snapshot=dict(final_output) if isinstance(final_output, dict) else None,
            meta=_node_meta,
        )

    # ------------------------------------------------------------------
    # Validation lifecycle helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Main execution entry point
    # ------------------------------------------------------------------

    def execute(self, *, revision_id: str, strict_determinism: bool = False) -> ExecutionTrace:
        """Execute the engine graph with a required validation lifecycle.

        Validation lifecycle (enforced, cannot be bypassed):

          Phase 1 — Pre-Validation: Structural (always blocking)
          Phase 1b — Pre-Validation: Determinism (strict mode only, blocking)
          Phase 2 — Execution
          Phase 3 — Post-Validation: Determinism (non-strict mode, advisory)
          Phase 4 — Trace Finalization (artifact commit boundary)

        Governance delegation:
          Phases 1, 1b, 3, and 4-decision are delegated to
          EngineGovernanceOrchestrator. Engine.execute() owns Phase 2 (node
          execution) and assembles the final ExecutionTrace from orchestrator
          results.

        Args:
            revision_id: Revision identifier for this execution.
            strict_determinism: If True, determinism validation is blocking
                pre-execution (Phase 1b).  If False (default), determinism
                validation is advisory post-execution (Phase 3).
        """
        from .validation.governance_orchestrator import EngineGovernanceOrchestrator

        started_at = now_utc()
        execution_id = str(uuid.uuid4())

        # ── Phases 1 + 1b + Pre-decision: delegated to orchestrator ──────────
        _gov = EngineGovernanceOrchestrator()
        pre_gov = _gov.run_pre(self, revision_id=revision_id, strict_determinism=strict_determinism)

        execution_allowed = pre_gov.execution_allowed
        primary_validation = pre_gov.primary_validation

        # ── Phase 2: Execution ────────────────────────────────────────────────
        if self.graph_runtime is not None and execution_allowed:
            circuit = {
                "nodes": [{"id": nid} for nid in self.node_ids],
                "edges": [
                    {"from": ch.src_node_id, "to": ch.dst_node_id, "channel": ch.channel_id}
                    for ch in self.channels
                ],
                "entry": self.entry_node_id,
                "flow": [
                    {"rule_id": fr.rule_id, "node_id": fr.node_id, "policy": fr.policy.value}
                    for fr in self.flow
                ],
            }
            graph_result = self.graph_runtime.execute(circuit=circuit, state={})

            node_traces: Dict[str, NodeTrace] = {
                nid: NodeTrace(
                    node_id=nid,
                    node_status=NodeStatus.NOT_REACHED,
                    pre_status=StageStatus.SKIPPED,
                    core_status=StageStatus.SKIPPED,
                    post_status=StageStatus.SKIPPED,
                    input_snapshot=None,
                    output_snapshot=None,
                    meta=None,
                )
                for nid in self.node_ids
            }

            graph_outputs = getattr(graph_result.trace, "node_outputs", {})
            graph_statuses = getattr(graph_result.trace, "node_statuses", {})
            graph_inputs = getattr(graph_result.trace, "node_inputs", {})
            graph_messages = getattr(graph_result.trace, "node_messages", {})
            for nid in self.node_ids:
                status_value = graph_statuses.get(nid)
                if status_value is None:
                    continue

                output = graph_outputs.get(nid)
                if isinstance(output, dict):
                    output_snapshot = dict(output)
                elif output is None:
                    output_snapshot = None
                else:
                    output_snapshot = {"output": output}

                input_snapshot = graph_inputs.get(nid)
                if isinstance(input_snapshot, dict):
                    input_snapshot = dict(input_snapshot)
                else:
                    input_snapshot = None

                if status_value == "success":
                    node_status = NodeStatus.SUCCESS
                    core_status = StageStatus.SUCCESS
                elif status_value == "failure":
                    node_status = NodeStatus.FAILURE
                    core_status = StageStatus.FAILURE
                elif status_value == "skipped":
                    node_status = NodeStatus.SKIPPED
                    core_status = StageStatus.SKIPPED
                else:
                    node_status = NodeStatus.NOT_REACHED
                    core_status = StageStatus.SKIPPED

                node_traces[nid] = NodeTrace(
                    node_id=nid,
                    node_status=node_status,
                    pre_status=StageStatus.SKIPPED,
                    core_status=core_status,
                    post_status=StageStatus.SKIPPED,
                    input_snapshot=input_snapshot,
                    output_snapshot=output_snapshot,
                    message=graph_messages.get(nid),
                    meta=None,
                )

            finished_at = now_utc()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)

            # ── Phase 3 + 4-decision: delegated to orchestrator ───────────────
            post_gov = _gov.run_post(
                self, revision_id=revision_id,
                strict_determinism=strict_determinism,
            )

            # ── Phase 4: Trace finalization (artifact commit boundary) ─────────
            trace_meta = {
                "engine_meta": self.meta,
                "delegated_via": "graph_runtime",
                "graph_trace": {
                    "run_id": getattr(graph_result.trace, "run_id", None),
                    "node_sequence": list(getattr(graph_result.trace, "node_sequence", [])),
                },
                "spec_versions": {
                    "execution_model": ENGINE_EXECUTION_MODEL_VERSION,
                    "trace_model": ENGINE_TRACE_MODEL_VERSION,
                },
                "validation": _gov.build_legacy_validation_meta(pre_gov, revision_id),
                "pre_validation": _gov.build_pre_validation_meta(pre_gov),
                "post_validation": _gov.build_post_validation_meta(post_gov, strict_determinism),
                "decision": _gov.build_decision_meta(pre_gov, post_gov),
            }

            return ExecutionTrace(
                execution_id=execution_id,
                revision_id=revision_id,
                structural_fingerprint=primary_validation.structural_fingerprint,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
                validation_success=primary_validation.success,
                validation_violations=[
                    {
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "severity": v.severity.value,
                        "location_type": v.location_type,
                        "location_id": v.location_id,
                        "message": v.message,
                    }
                    for v in primary_validation.violations
                ],
                nodes=node_traces,
                meta=trace_meta,
                expected_node_ids=self.node_ids,
            )

        # ── Phase 2 (direct handler path) ─────────────────────────────────────
        node_traces: Dict[str, NodeTrace] = {
            nid: NodeTrace(
                node_id=nid,
                node_status=NodeStatus.NOT_REACHED,
                pre_status=StageStatus.SKIPPED,
                core_status=StageStatus.SKIPPED,
                post_status=StageStatus.SKIPPED,
                input_snapshot=None,
                output_snapshot=None,
                meta=None,
            )
            for nid in self.node_ids
        }

        if execution_allowed and self.entry_node_id in node_traces:
            reverse = self._build_reverse_graph()

            # Node-level flow policy map (default ALL_SUCCESS)
            flow_policy: Dict[str, FlowPolicy] = {nid: FlowPolicy.ALL_SUCCESS for nid in self.node_ids}
            for fr in self.flow:
                if fr.node_id in flow_policy:
                    flow_policy[fr.node_id] = fr.policy

            # Execute entry
            entry_trace = self._apply_retry(self.entry_node_id, {})
            if entry_trace.node_status == NodeStatus.FAILURE:
                entry_trace = self._apply_fallback(self.entry_node_id, entry_trace, {})
            node_traces[self.entry_node_id] = entry_trace

            # Deterministic, monotonic fixpoint loop:
            # NOT_REACHED -> (SUCCESS|FAILURE|SKIPPED) only, until no change.
            changed = True
            while changed:
                changed = False
                for node_id in self.node_ids:
                    if node_id == self.entry_node_id:
                        continue

                    current = node_traces[node_id].node_status
                    if current != NodeStatus.NOT_REACHED:
                        continue

                    parents = reverse.get(node_id, [])
                    if not parents:
                        continue

                    parent_statuses = [node_traces[p].node_status for p in parents]

                    policy = flow_policy.get(node_id, FlowPolicy.ALL_SUCCESS)

                    # ── Failure Propagation Policy ─────────────────────────────
                    # Applied BEFORE flow policy logic.
                    # Default is STRICT (backward compatible).
                    failure_policy = self.node_failure_policies.get(node_id, NodeFailurePolicy.STRICT)

                    # CASCADE_FAIL: any upstream FAILURE → this node becomes FAILURE immediately.
                    if failure_policy == NodeFailurePolicy.CASCADE_FAIL:
                        if any(s == NodeStatus.FAILURE for s in parent_statuses):
                            node_traces[node_id] = NodeTrace(
                                node_id=node_id,
                                node_status=NodeStatus.FAILURE,
                                pre_status=StageStatus.SKIPPED,
                                core_status=StageStatus.SKIPPED,
                                post_status=StageStatus.SKIPPED,
                                reason_code="ENG-CASCADE-FAIL",
                                message="upstream FAILURE propagated via CASCADE_FAIL policy",
                            )
                            changed = True
                            continue

                    # ISOLATE: treat upstream FAILURE as NOT_REACHED for propagation purposes.
                    # Recompute parent_statuses with FAILURE replaced by NOT_REACHED.
                    if failure_policy == NodeFailurePolicy.ISOLATE:
                        parent_statuses = [
                            NodeStatus.NOT_REACHED if s == NodeStatus.FAILURE else s
                            for s in parent_statuses
                        ]
                        # If all effective statuses are NOT_REACHED, defer — nothing to act on yet.
                        if all(s == NodeStatus.NOT_REACHED for s in parent_statuses):
                            # All parents are either FAILURE (ignored) or actually NOT_REACHED.
                            # If all original parents are terminal (FAILURE or SKIPPED), skip.
                            orig = [node_traces[p].node_status for p in parents]
                            if all(s in (NodeStatus.FAILURE, NodeStatus.SKIPPED) for s in orig):
                                node_traces[node_id] = NodeTrace(
                                    node_id=node_id,
                                    node_status=NodeStatus.SKIPPED,
                                    pre_status=StageStatus.SKIPPED,
                                    core_status=StageStatus.SKIPPED,
                                    post_status=StageStatus.SKIPPED,
                                    reason_code="ENG-UPSTREAM-NO-SUCCESS",
                                    message="no upstream success available (ISOLATE policy)",
                                )
                                changed = True
                            continue

                    # v1 deterministic reachability rules:
                    # - A node runs when its flow policy is satisfied.
                    # - A node becomes SKIPPED only when the policy becomes *impossible* to satisfy
                    #   given terminal upstream states.
                    # - NOT_REACHED upstreams are treated as "pending".
                    should_run = False
                    should_skip = False
                    skip_reason_code = None
                    skip_message = None

                    if policy == FlowPolicy.ALL_SUCCESS:
                        # Any terminal non-success upstream makes ALL_SUCCESS impossible.
                        if any(s in (NodeStatus.FAILURE, NodeStatus.SKIPPED) for s in parent_statuses):
                            should_skip = True
                            skip_reason_code = "ENG-UPSTREAM-FAIL"
                            skip_message = "upstream failure prevents ALL_SUCCESS"
                        elif all(s == NodeStatus.SUCCESS for s in parent_statuses):
                            should_run = True
                        else:
                            # Some upstreams are still NOT_REACHED; defer.
                            pass

                    elif policy in (FlowPolicy.ANY_SUCCESS, FlowPolicy.FIRST_SUCCESS):
                        # v1 minimal semantics: FIRST_SUCCESS behaves like ANY_SUCCESS
                        if any(s == NodeStatus.SUCCESS for s in parent_statuses):
                            should_run = True
                        elif all(s in (NodeStatus.FAILURE, NodeStatus.SKIPPED) for s in parent_statuses):
                            # No upstream can ever succeed.
                            should_skip = True
                            skip_reason_code = "ENG-UPSTREAM-NO-SUCCESS"
                            skip_message = "no upstream success satisfies ANY_SUCCESS"
                        else:
                            # Pending upstreams remain NOT_REACHED; defer.
                            pass

                    if should_skip:
                        node_traces[node_id] = NodeTrace(
                            node_id=node_id,
                            node_status=NodeStatus.SKIPPED,
                            pre_status=StageStatus.SKIPPED,
                            core_status=StageStatus.SKIPPED,
                            post_status=StageStatus.SKIPPED,
                            reason_code=skip_reason_code,
                            message=skip_message,
                        )
                        changed = True
                        continue

                    if not should_run:
                        continue

                    # Build merged input snapshot from upstream outputs (namespaced by parent node_id).
                    merged_input: Dict[str, Any] = {}
                    for p in parents:
                        out = node_traces[p].output_snapshot
                        if out is not None:
                            merged_input[p] = dict(out)

                    node_trace = self._apply_retry(node_id, merged_input)
                    if node_trace.node_status == NodeStatus.FAILURE:
                        node_trace = self._apply_fallback(node_id, node_trace, merged_input)
                    node_traces[node_id] = node_trace
                    changed = True

        finished_at = now_utc()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        # ── Phase 3 + 4-decision: delegated to orchestrator ─────────────────
        post_gov = _gov.run_post(
            self, revision_id=revision_id,
            strict_determinism=strict_determinism,
        )

        # ── Phase 4: Trace finalization (artifact commit boundary) ─────────────
        trace_meta = {
            "engine_meta": self.meta,
            "spec_versions": {
                "execution_model": ENGINE_EXECUTION_MODEL_VERSION,
                "trace_model": ENGINE_TRACE_MODEL_VERSION,
            },
            "validation": _gov.build_legacy_validation_meta(pre_gov, revision_id),
            "pre_validation": _gov.build_pre_validation_meta(pre_gov),
            "post_validation": _gov.build_post_validation_meta(post_gov, strict_determinism),
            "decision": _gov.build_decision_meta(pre_gov, post_gov),
        }

        trace = ExecutionTrace(
            execution_id=execution_id,
            revision_id=revision_id,
            structural_fingerprint=primary_validation.structural_fingerprint,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            validation_success=primary_validation.success,
            validation_violations=[
                {
                    "rule_id": v.rule_id,
                    "rule_name": v.rule_name,
                    "severity": v.severity.value,
                    "location_type": v.location_type,
                    "location_id": v.location_id,
                    "message": v.message,
                }
                for v in primary_validation.violations
            ],
            nodes=node_traces,
            meta=trace_meta,
            expected_node_ids=self.node_ids,
        )

        return trace


# --- ExecutionEnvironment v2 integration ---
from src.engine.environment_fingerprint import compute_environment_fingerprint
import hashlib

def _compute_execution_fingerprint(structural_fingerprint, env_fp):
    raw = f"{structural_fingerprint}:{env_fp}"
    return hashlib.sha256(raw.encode()).hexdigest()
