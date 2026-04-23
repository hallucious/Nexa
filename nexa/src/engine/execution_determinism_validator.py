from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from src.engine.execution_replay import ReplayResult


@dataclass
class NodeDeterminismResult:
    node_id: str
    deterministic: bool
    expected_output: Any
    replay_output: Any
    reason: Optional[str] = None


@dataclass
class DeterminismReport:
    execution_id: str
    deterministic: bool
    node_results: List[NodeDeterminismResult]


class ExecutionDeterminismValidator:
    """
    Validate whether replayed node outputs match expected node outputs.

    v1 scope:
    - compare expected output vs replay output
    - mark node-level deterministic / non-deterministic
    - return overall execution verdict
    """

    def validate(
        self,
        *,
        execution_id: str,
        expected_outputs: dict[str, Any],
        replay_result: ReplayResult,
    ) -> DeterminismReport:
        node_results: List[NodeDeterminismResult] = []
        overall_deterministic = True

        replay_map = {result.node_id: result for result in replay_result.node_results}

        for node_id, expected_output in expected_outputs.items():
            replay_node = replay_map.get(node_id)

            if replay_node is None:
                overall_deterministic = False
                node_results.append(
                    NodeDeterminismResult(
                        node_id=node_id,
                        deterministic=False,
                        expected_output=expected_output,
                        replay_output=None,
                        reason="node missing in replay",
                    )
                )
                continue

            if replay_node.success is False:
                overall_deterministic = False
                node_results.append(
                    NodeDeterminismResult(
                        node_id=node_id,
                        deterministic=False,
                        expected_output=expected_output,
                        replay_output=replay_node.output,
                        reason=replay_node.error or "replay failed",
                    )
                )
                continue

            if replay_node.output != expected_output:
                overall_deterministic = False
                node_results.append(
                    NodeDeterminismResult(
                        node_id=node_id,
                        deterministic=False,
                        expected_output=expected_output,
                        replay_output=replay_node.output,
                        reason="output mismatch",
                    )
                )
            else:
                node_results.append(
                    NodeDeterminismResult(
                        node_id=node_id,
                        deterministic=True,
                        expected_output=expected_output,
                        replay_output=replay_node.output,
                    )
                )

        return DeterminismReport(
            execution_id=execution_id,
            deterministic=overall_deterministic,
            node_results=node_results,
        )