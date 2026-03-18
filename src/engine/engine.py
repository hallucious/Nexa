from __future__ import annotations
from src.utils.time import now_utc, now_utc_iso

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

from src.contracts.spec_versions import (
    ENGINE_EXECUTION_MODEL_VERSION,
    ENGINE_TRACE_MODEL_VERSION,
    VALIDATION_ENGINE_CONTRACT_VERSION,
    VALIDATION_RULE_CATALOG_VERSION,
)

from .fingerprint import StructuralFingerprint, compute_fingerprint
from .model import Channel, EngineStructure, FlowRule
from .revision import Revision
from .trace import ExecutionTrace, NodeTrace
from .types import FlowPolicy, NodeStatus, StageStatus
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


    def _run_node(self, *, node_id: str, input_snapshot: Dict[str, Any]) -> NodeTrace:
        """Run node using pre / core / post stages.

        Backward compatible:
        - If handlers[node_id] is a callable: treated as Core handler.
        - If handlers[node_id] is a dict with pre/core/post: staged handler (pre/core/post dict).
        """
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
        )

    # ------------------------------------------------------------------
    # Validation lifecycle helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_pre_validation_meta(structural_result, pre_det_result) -> Dict[str, Any]:
        """Build trace.meta['pre_validation'] block."""
        block: Dict[str, Any] = {
            "structural": {
                "performed": True,
                "success": structural_result.success,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "severity": v.severity.value,
                        "location_type": v.location_type,
                        "location_id": v.location_id,
                        "message": v.message,
                    }
                    for v in structural_result.violations
                ],
            },
        }
        if pre_det_result is not None:
            block["determinism"] = {
                "performed": True,
                "strict_mode": True,
                "success": pre_det_result.success,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "severity": v.severity.value,
                        "location_type": v.location_type,
                        "location_id": v.location_id,
                        "message": v.message,
                    }
                    for v in pre_det_result.violations
                ],
            }
        else:
            block["determinism"] = {"performed": False}
        return block

    @staticmethod
    def _build_post_validation_meta(post_det_result, strict_determinism: bool) -> Dict[str, Any]:
        """Build trace.meta['post_validation'] block."""
        if post_det_result is not None:
            return {
                "performed": True,
                "strict_mode": strict_determinism,
                "success": post_det_result.success,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "severity": v.severity.value,
                        "location_type": v.location_type,
                        "location_id": v.location_id,
                        "message": v.message,
                    }
                    for v in post_det_result.violations
                ],
            }
        return {"performed": False}

    # ------------------------------------------------------------------
    # Main execution entry point
    # ------------------------------------------------------------------

    def execute(self, *, revision_id: str, strict_determinism: bool = False) -> ExecutionTrace:
        """Execute the engine graph with a required validation lifecycle.

        Validation lifecycle (enforced, cannot be bypassed):

          Phase 1 — Pre-Validation: Structural (always blocking)
            Structural validation runs before any node executes.
            Hard failure prevents all execution; all nodes remain NOT_REACHED.

          Phase 1b — Pre-Validation: Determinism (strict mode only, blocking)
            In strict mode, determinism config validation is also blocking
            pre-execution.  A failure here prevents execution identically to
            a structural failure.

          Phase 2 — Execution
            Nodes execute only when Phase 1 (and 1b in strict mode) succeeded.

          Phase 3 — Post-Validation: Determinism (non-strict mode, advisory)
            In non-strict mode, determinism config validation runs AFTER
            execution completes.  Findings are advisory: they do not alter
            already-produced node outputs but are recorded in the trace so
            callers can observe them.

          Phase 4 — Trace Finalization (artifact commit boundary)
            The ExecutionTrace (containing all node output_snapshots / artifacts)
            is constructed and returned only AFTER Phase 3 completes.  This
            guarantees that post-validation results are embedded in the trace
            before it is surfaced to any caller.

        Args:
            revision_id: Revision identifier for this execution.
            strict_determinism: If True, determinism validation is blocking
                pre-execution (Phase 1b).  If False (default), determinism
                validation is advisory post-execution (Phase 3).
        """
        from .validation.validator import ValidationEngine

        started_at = now_utc()
        execution_id = str(uuid.uuid4())

        validator = ValidationEngine()

        # ── Phase 1: Pre-validation — structural (always blocking) ────────────
        structural_validation = validator.validate_structural(self, revision_id=revision_id)

        # ── Phase 1b: Pre-validation — determinism (strict mode only, blocking)
        pre_determinism_validation = None
        if strict_determinism:
            pre_determinism_validation = validator.validate_determinism(
                self, revision_id=revision_id, strict_determinism=True
            )

        # ── Decision Policy: map pre-validation results → pre-decision ──────────
        from .validation.decision_policy import ValidationDecisionPolicy
        decision_policy = ValidationDecisionPolicy()

        pre_decision = decision_policy.decide_pre(
            structural_validation, pre_determinism_validation
        )
        execution_allowed = not pre_decision.blocks_execution

        # The trace's top-level validation fields reflect the blocking validation
        # (structural, or strict determinism if that failed).
        if pre_determinism_validation is not None and not pre_determinism_validation.success:
            # Strict determinism failure: surface it as the primary validation result.
            primary_validation = pre_determinism_validation
        else:
            primary_validation = structural_validation

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

            # ── Phase 3: Post-validation — determinism (non-strict, advisory) ──
            post_determinism_validation = None
            if not strict_determinism:
                post_determinism_validation = validator.validate_determinism(
                    self, revision_id=revision_id, strict_determinism=False
                )

            # ── Decision Policy: map post-validation result → post-decision ────
            post_decision = decision_policy.decide_post(
                post_determinism_validation, strict_determinism=strict_determinism
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
                # Legacy key: structural validation info (backward compat)
                "validation": {
                    "at": now_utc_iso(),
                    "contract_version": VALIDATION_ENGINE_CONTRACT_VERSION,
                    "rule_catalog_version": VALIDATION_RULE_CATALOG_VERSION,
                    "snapshot": {
                        "snapshot_version": "1",
                        "applied_rules": sorted(set(getattr(structural_validation, "applied_rule_ids", []))),
                    },
                },
                # Explicit lifecycle phases
                "pre_validation": self._build_pre_validation_meta(
                    structural_validation, pre_determinism_validation
                ),
                "post_validation": self._build_post_validation_meta(
                    post_determinism_validation, strict_determinism
                ),
                # Decision outcomes (policy layer)
                "decision": {
                    "pre": {
                        "value": pre_decision.decision.value,
                        "reason": pre_decision.reason,
                    },
                    "post": {
                        "value": post_decision.decision.value,
                        "reason": post_decision.reason,
                    },
                },
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
            node_traces[self.entry_node_id] = self._run_node(node_id=self.entry_node_id, input_snapshot={})

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

                    node_traces[node_id] = self._run_node(node_id=node_id, input_snapshot=merged_input)
                    changed = True

        finished_at = now_utc()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        # ── Phase 3: Post-validation — determinism (non-strict, advisory) ──────
        post_determinism_validation = None
        if not strict_determinism:
            post_determinism_validation = validator.validate_determinism(
                self, revision_id=revision_id, strict_determinism=False
            )

        # ── Decision Policy: map post-validation result → post-decision ────────
        post_decision = decision_policy.decide_post(
            post_determinism_validation, strict_determinism=strict_determinism
        )

        # ── Phase 4: Trace finalization (artifact commit boundary) ─────────────
        # The trace is constructed only after post-validation completes.
        # Post-validation outcomes are embedded before the trace is returned.
        trace_meta = {
            "engine_meta": self.meta,
            "spec_versions": {
                "execution_model": ENGINE_EXECUTION_MODEL_VERSION,
                "trace_model": ENGINE_TRACE_MODEL_VERSION,
            },
            # Legacy key: structural validation info (backward compat)
            "validation": {
                "at": now_utc_iso(),
                "contract_version": VALIDATION_ENGINE_CONTRACT_VERSION,
                "rule_catalog_version": VALIDATION_RULE_CATALOG_VERSION,
                "snapshot": {
                    "snapshot_version": "1",
                    "applied_rules": sorted(set(getattr(structural_validation, "applied_rule_ids", []))),
                },
            },
            # Explicit lifecycle phases
            "pre_validation": self._build_pre_validation_meta(
                structural_validation, pre_determinism_validation
            ),
            "post_validation": self._build_post_validation_meta(
                post_determinism_validation, strict_determinism
            ),
            # Decision outcomes (policy layer)
            "decision": {
                "pre": {
                    "value": pre_decision.decision.value,
                    "reason": pre_decision.reason,
                },
                "post": {
                    "value": post_decision.decision.value,
                    "reason": post_decision.reason,
                },
            },
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
