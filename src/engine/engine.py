from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .fingerprint import StructuralFingerprint, compute_fingerprint
from .model import Channel, EngineStructure, FlowRule
from .revision import Revision
from .trace import ExecutionTrace, NodeTrace
from .types import FlowPolicy, NodeStatus, StageStatus


# Minimal handler signature for v1 execution:
# - input_data: merged upstream outputs (namespaced by parent node_id)
# - output: dict that will be snapshotted into trace
NodeHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class Engine:
    entry_node_id: str
    node_ids: List[str]
    channels: List[Channel] = field(default_factory=list)
    flow: List[FlowRule] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    # Node execution handlers (optional).
    # If a node is reached but no handler is registered, the engine uses a default no-op handler.
    handlers: Dict[str, NodeHandler] = field(default_factory=dict, repr=False)

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
        handler = self.handlers.get(node_id) or self._noop_handler
        # pre/core/post pipeline is minimal in v1:
        # - pre: SUCCESS
        # - core: SUCCESS if handler returns; FAILURE if exception
        # - post: SUCCESS if core SUCCESS, else SKIPPED
        try:
            output = handler(dict(input_snapshot))
            if output is None:
                output = {}
            if not isinstance(output, dict):
                raise TypeError(f"handler output must be dict, got {type(output).__name__}")
            return NodeTrace(
                node_id=node_id,
                node_status=NodeStatus.SUCCESS,
                pre_status=StageStatus.SUCCESS,
                core_status=StageStatus.SUCCESS,
                post_status=StageStatus.SUCCESS,
                input_snapshot=dict(input_snapshot),
                output_snapshot=dict(output),
            )
        except Exception as e:
            return NodeTrace(
                node_id=node_id,
                node_status=NodeStatus.FAILURE,
                pre_status=StageStatus.SUCCESS,
                core_status=StageStatus.FAILURE,
                post_status=StageStatus.SKIPPED,
                reason_code="ENG-EXC",
                message=str(e),
                input_snapshot=dict(input_snapshot),
                output_snapshot=None,
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

                    # FAILURE dominates: downstream is SKIPPED (v1 contract)
                    if any(s == NodeStatus.FAILURE for s in parent_statuses):
                        node_traces[node_id] = NodeTrace(
                            node_id=node_id,
                            node_status=NodeStatus.SKIPPED,
                            pre_status=StageStatus.SKIPPED,
                            core_status=StageStatus.SKIPPED,
                            post_status=StageStatus.SKIPPED,
                            reason_code="ENG-UPSTREAM-FAIL",
                            message="upstream failure",
                        )
                        changed = True
                        continue

                    policy = flow_policy.get(node_id, FlowPolicy.ALL_SUCCESS)

                    should_run = False
                    if policy == FlowPolicy.ALL_SUCCESS:
                        should_run = all(s == NodeStatus.SUCCESS for s in parent_statuses)
                    elif policy == FlowPolicy.ANY_SUCCESS:
                        should_run = any(s == NodeStatus.SUCCESS for s in parent_statuses)
                    elif policy == FlowPolicy.FIRST_SUCCESS:
                        # v1 minimal semantics: treat FIRST_SUCCESS as ANY_SUCCESS (no time model yet)
                        should_run = any(s == NodeStatus.SUCCESS for s in parent_statuses)

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
            validation_violations=[(v.rule_id, v.message) for v in validation.violations],
            nodes=node_traces,
            meta={"engine_meta": self.meta},
            expected_node_ids=self.node_ids,
        )

        return trace
