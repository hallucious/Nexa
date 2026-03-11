from __future__ import annotations

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
    Deterministic true replay engine.

    v1 scope:
    - replay nodes in observed order
    - re-execute each node through CircuitRunner.run_single_node()
    - compare replayed node outputs with expected outputs
    """

    def replay(
        self,
        *,
        plan: ReplayPlan,
        circuit_runner,
        circuit: Dict[str, Any],
        input_state: Dict[str, Any],
        expected_outputs: Optional[Dict[str, Any]] = None,
    ) -> ReplayResult:
        current_state = dict(input_state)
        node_results: List[ReplayNodeResult] = []
        overall_success = True

        for node_id in plan.node_order:
            try:
                output = circuit_runner.run_single_node(
                    circuit=circuit,
                    node_id=node_id,
                    state=current_state,
                )

                if expected_outputs is not None:
                    expected = expected_outputs.get(node_id)
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
                    else:
                        node_results.append(
                            ReplayNodeResult(
                                node_id=node_id,
                                success=True,
                                output=output,
                            )
                        )
                else:
                    node_results.append(
                        ReplayNodeResult(
                            node_id=node_id,
                            success=True,
                            output=output,
                        )
                    )

                current_state[node_id] = output

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

        return ReplayResult(
            execution_id=plan.execution_id,
            success=overall_success,
            node_results=node_results,
        )