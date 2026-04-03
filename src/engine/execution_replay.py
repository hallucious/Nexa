from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.engine.execution_timeline import ExecutionTimeline


@dataclass
class ReplayPlan:
    execution_id: str
    node_order: List[str]


@dataclass
class ReplayNodeResult:
    node_id: str
    success: bool
    output: Any
    error: Optional[str] = None


@dataclass
class ReplayResult:
    execution_id: str
    success: bool
    node_results: List[ReplayNodeResult]


class ReplayPlanner:
    """
    Build a deterministic replay order from an execution timeline.

    v1 rule:
    - sort node spans by start_ms
    - preserve observed node execution order
    """

    def build_plan(self, timeline: ExecutionTimeline) -> ReplayPlan:
        ordered_spans = sorted(
            timeline.node_spans,
            key=lambda span: (span.start_ms, span.node_id),
        )

        return ReplayPlan(
            execution_id=timeline.execution_id,
            node_order=[span.node_id for span in ordered_spans],
        )


class ExecutionReplayEngine:
    """
    Deterministic replay engine.

    Closure scope:
    - replay nodes in observed order
    - rebuild per-node input snapshots using edge/channel propagation
    - re-execute each node through CircuitRunner.run_single_node()
    - compare replayed node outputs with expected outputs
    - fail closed when a replayed node is missing required parent outputs
    """

    @staticmethod
    def _build_edge_lookups(
        circuit: Dict[str, Any],
    ) -> tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
        outgoing: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        reverse: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for edge in circuit.get("edges", []):
            if not isinstance(edge, dict):
                continue
            src = edge.get("from")
            dst = edge.get("to")
            if not isinstance(src, str) or not src:
                continue
            if not isinstance(dst, str) or not dst:
                continue
            outgoing[src].append(edge)
            reverse[dst].append(edge)

        return outgoing, reverse

    def replay(
        self,
        *,
        plan: ReplayPlan,
        circuit_runner,
        circuit: Dict[str, Any],
        input_state: Dict[str, Any],
        expected_outputs: Optional[Dict[str, Any]] = None,
    ) -> ReplayResult:
        outgoing, reverse = self._build_edge_lookups(circuit)
        current_state = dict(input_state)
        node_output_map: Dict[str, Any] = {}
        node_results: List[ReplayNodeResult] = []
        overall_success = True

        for node_id in plan.node_order:
            replay_state = dict(current_state)
            missing_parents: List[str] = []

            for edge in reverse.get(node_id, []):
                src = edge.get("from")
                if not isinstance(src, str) or not src:
                    continue
                if src not in node_output_map:
                    missing_parents.append(src)
                    continue
                channel = edge.get("channel")
                if not isinstance(channel, str) or not channel:
                    channel = src
                replay_state[channel] = node_output_map[src]
                replay_state[src] = node_output_map[src]

            if missing_parents:
                overall_success = False
                node_results.append(
                    ReplayNodeResult(
                        node_id=node_id,
                        success=False,
                        output=None,
                        error=(
                            "replay missing parent outputs for "
                            f"{node_id}: {', '.join(sorted(set(missing_parents)))}"
                        ),
                    )
                )
                continue

            try:
                output = circuit_runner.run_single_node(
                    circuit=circuit,
                    node_id=node_id,
                    state=replay_state,
                )
            except Exception as exc:
                overall_success = False
                node_results.append(
                    ReplayNodeResult(
                        node_id=node_id,
                        success=False,
                        output=None,
                        error=str(exc),
                    )
                )
                continue

            node_output_map[node_id] = output

            for edge in outgoing.get(node_id, []):
                channel = edge.get("channel")
                if not isinstance(channel, str) or not channel:
                    channel = node_id
                current_state[channel] = output

            if expected_outputs is not None and node_id in expected_outputs:
                expected = expected_outputs[node_id]
                if output != expected:
                    overall_success = False
                    node_results.append(
                        ReplayNodeResult(
                            node_id=node_id,
                            success=False,
                            output=output,
                            error=f"replay output mismatch: expected={expected!r} actual={output!r}",
                        )
                    )
                    continue

            node_results.append(
                ReplayNodeResult(
                    node_id=node_id,
                    success=True,
                    output=output,
                )
            )

        return ReplayResult(
            execution_id=plan.execution_id,
            success=overall_success,
            node_results=node_results,
        )
