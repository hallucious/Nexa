from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Generic, List, Set, TypeVar

from src.engine.compiled_resource_graph import CompiledResourceGraph


T = TypeVar("T")


class GraphSchedulerError(ValueError):
    """Raised when compiled graph scheduling cannot proceed."""


@dataclass(frozen=True)
class ExecutionWave:
    index: int
    resource_ids: List[str]


@dataclass
class GraphExecutionResult(Generic[T]):
    waves: List[ExecutionWave] = field(default_factory=list)
    resource_results: Dict[str, T] = field(default_factory=dict)


class GraphScheduler:
    """
    Wave-based scheduler for CompiledResourceGraph.

    Important invariants:
    - scheduling unit is always a resource
    - runtime consumes a DAG only (cycle must already be rejected at compile time)
    - ready-set is rebuilt from dependency counts
    - output resolution is NOT handled here
    """

    def __init__(self, graph: CompiledResourceGraph):
        self.graph = graph

    def _build_dependency_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for resource_id in self.graph.resources:
            counts[resource_id] = len(self.graph.dependencies.get(resource_id, set()))
        return counts

    def build_waves(self) -> List[ExecutionWave]:
        dependency_counts = self._build_dependency_counts()
        scheduled: Set[str] = set()
        waves: List[ExecutionWave] = []
        wave_index = 0

        while len(scheduled) < len(self.graph.resources):
            ready_set = sorted(
                resource_id
                for resource_id, count in dependency_counts.items()
                if count == 0 and resource_id not in scheduled
            )

            if not ready_set:
                unresolved = sorted(
                    resource_id
                    for resource_id in self.graph.resources
                    if resource_id not in scheduled
                )
                raise GraphSchedulerError(
                    "graph scheduling stalled; unresolved resources remain: "
                    + ", ".join(unresolved)
                )

            waves.append(ExecutionWave(index=wave_index, resource_ids=ready_set))

            for resource_id in ready_set:
                scheduled.add(resource_id)

            for resource_id in ready_set:
                for dependent in sorted(self.graph.dependents.get(resource_id, set())):
                    if dependent in scheduled:
                        continue
                    dependency_counts[dependent] -= 1
                    if dependency_counts[dependent] < 0:
                        raise GraphSchedulerError(
                            f"dependency count below zero for resource: {dependent}"
                        )

            wave_index += 1

        return waves

    def execute(
        self,
        executor: Callable[[str], T],
    ) -> GraphExecutionResult[T]:
        waves = self.build_waves()
        results = GraphExecutionResult[T](waves=waves)

        for wave in waves:
            for resource_id in wave.resource_ids:
                results.resource_results[resource_id] = executor(resource_id)

        return results