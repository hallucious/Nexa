from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, Generic, List, Optional, Set, TypeVar

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

    Execution modes
    ---------------
    execute()        — sync path; same-wave resources run via ThreadPoolExecutor
    execute_async()  — true async path; same-wave resources run via asyncio.gather()
                       Caller must be inside a running event loop.
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

    # ------------------------------------------------------------------
    # Sync execution path (ThreadPoolExecutor)
    # ------------------------------------------------------------------

    def execute(
        self,
        executor: Callable[[str], T],
        *,
        max_workers: Optional[int] = None,
    ) -> GraphExecutionResult[T]:
        """Execute waves synchronously; same-wave resources run in a ThreadPoolExecutor."""
        waves = self.build_waves()
        results = GraphExecutionResult[T](waves=waves)

        worker_limit = max_workers if isinstance(max_workers, int) and max_workers > 0 else None

        with ThreadPoolExecutor(max_workers=worker_limit) as pool:
            for wave in waves:
                if len(wave.resource_ids) <= 1:
                    for resource_id in wave.resource_ids:
                        results.resource_results[resource_id] = executor(resource_id)
                    continue

                future_map = {
                    resource_id: pool.submit(executor, resource_id)
                    for resource_id in wave.resource_ids
                }
                wave_results = {
                    resource_id: future.result()
                    for resource_id, future in future_map.items()
                }
                for resource_id in wave.resource_ids:
                    results.resource_results[resource_id] = wave_results[resource_id]

        return results

    # ------------------------------------------------------------------
    # True async execution path (asyncio.gather)
    # ------------------------------------------------------------------

    async def execute_async(
        self,
        executor: Callable[[str], Awaitable[T]],
    ) -> GraphExecutionResult[T]:
        """Execute waves using asyncio.gather for same-wave concurrency.

        Requirements
        ------------
        - ``executor`` must be an async callable: ``async def executor(resource_id) -> T``
        - Wave ordering is preserved: wave N+1 starts only after all of wave N completes
        - Same-wave resources execute concurrently via ``asyncio.gather()``
        - Must be called from inside a running asyncio event loop
        """
        waves = self.build_waves()
        results = GraphExecutionResult[T](waves=waves)

        for wave in waves:
            if len(wave.resource_ids) == 1:
                # Single resource: no gather overhead needed
                rid = wave.resource_ids[0]
                results.resource_results[rid] = await executor(rid)
            else:
                # Multiple resources: execute concurrently within this wave
                tasks = [executor(rid) for rid in wave.resource_ids]
                wave_results = await asyncio.gather(*tasks)
                for rid, result in zip(wave.resource_ids, wave_results):
                    results.resource_results[rid] = result

        return results
