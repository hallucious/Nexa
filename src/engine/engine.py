from __future__ import annotations

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


# Handler signatures for v1.5 execution (Step48):
# - Core handler: input_snapshot -> output_snapshot
# - Pipeline handler: dict with optional "pre"/"core"/"post" callables
CoreHandler = Callable[[Dict[str, Any]], Dict[str, Any]]
PreHandler = Callable[[Dict[str, Any]], Dict[str, Any]]
PostHandler = Callable[[Dict[str, Any]], Dict[str, Any]]

NodeHandler = CoreHandler  # backward-compatible alias

def _is_pipeline_handler(obj: Any) -> bool:
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
        """Run node using mandatory Pre → Core → Post pipeline.

        Backward compatible:
        - If handlers[node_id] is a callable: treated as Core handler.
        - If handlers[node_id] is a dict with pre/core/post: pipeline handler.
        """
        handler_obj = self.handlers.get(node_id)

        pre_fn: Optional[PreHandler] = None
        core_fn: Optional[CoreHandler] = None
        post_fn: Optional[PostHandler] = None

        if handler_obj is None:
            core_fn = self._noop_handler
        elif callable(handler_obj):
            core_fn = handler_obj  # type: ignore[assignment]
        elif _is_pipeline_handler(handler_obj):
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

    def execute(self, *, revision_id: str) -> ExecutionTrace:
        """Step47: Execute reached nodes using handlers, then propagate reachability with FlowRule policies.

        - Validation must pass for any execution.
        - Entry node is executed first.
        - Downstream nodes are executed when their FlowPolicy condition is satisfied.
        - Failure on any upstream parent causes downstream nodes to be SKIPPED (v1 semantics).
        """
        from .validation.validator import ValidationEngine

        started_at = datetime.utcnow()
        execution_id = str(uuid.uuid4())

        validation = ValidationEngine().validate(self, revision_id=revision_id)

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

        if validation.success and self.entry_node_id in node_traces:
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

        finished_at = datetime.utcnow()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        trace = ExecutionTrace(
            execution_id=execution_id,
            revision_id=revision_id,
            structural_fingerprint=validation.structural_fingerprint,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            validation_success=validation.success,
            validation_violations=[
                {
                    "rule_id": v.rule_id,
                    "rule_name": v.rule_name,
                    "severity": v.severity.value,
                    "location_type": v.location_type,
                    "location_id": v.location_id,
                    "message": v.message,
                }
                for v in validation.violations
            ],
            nodes=node_traces,
            meta={
                "engine_meta": self.meta,
                "spec_versions": {
                    "execution_model": ENGINE_EXECUTION_MODEL_VERSION,
                    "trace_model": ENGINE_TRACE_MODEL_VERSION,
                },
                "validation": {
                    "at": datetime.utcnow().isoformat(),
                    "contract_version": VALIDATION_ENGINE_CONTRACT_VERSION,
                    "rule_catalog_version": VALIDATION_RULE_CATALOG_VERSION,
                },
            },
            expected_node_ids=self.node_ids,
        )

        return trace
